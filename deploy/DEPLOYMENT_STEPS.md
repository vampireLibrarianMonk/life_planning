# Deployment — As-Built Runbook (Phase 1, single region us-east-1)

The Life Plan Tracker is **live** at `https://life-planning.my-deployment.com`
on AWS App Runner. This is the **as-built** record — what actually exists and
how it was built — not a plan. For the design rationale see
`DEPLOYMENT_STRATEGY.md`; for per-step security verification see
`SECURITY_GATES.md`; for deferred work see `FOLLOW_UPS.md`.

- **Account:** 809784555426  **Region:** us-east-1
- **Admin identity:** IAM user `house-user` (console/CLI only — never used by
  the app; the app assumes its own role)
- **Route 53 zones:** `my-deployment.com` = `Z0101762W5VWFT32BT2B` (app domain),
  `housing-planner.com` = `Z02860032ZNCH6LLUL27W` (unrelated)

> **ARN convention:** every resource's ARN/ID/name lives in the git-ignored
> `.arn-env` file at the repo root — the single source of truth. Source it
> before running any command: `set -a; . ./.arn-env; set +a`. `monitor.sh`
> and `build_push.sh` rely on it. All 13 app resources are tagged
> `project=life-planning` (activated as a cost-allocation tag) so spend can be
> filtered in Cost Explorer; the Route 53 zone is intentionally untagged
> (shared infra).

---

## Key architecture decision: ECR image, not GitHub source

App Runner's CLI/API source-build only supports **managed runtimes** (no
Docker). Our app needs a multi-stage Dockerfile (build the React frontend, then
run FastAPI serving both). So we build the image locally and push to **ECR**,
and App Runner deploys from the ECR image with **auto-deploy on `:latest`**.

A GitHub connection (`life-planning-github`) was created and is `AVAILABLE`, but
is **not** the active source — it is retained for a possible future switch to
source-based builds.

Redeploy = `./deploy/build_push.sh` (build → push `:latest` + timestamp tag →
App Runner auto-rolls). ECR lifecycle policy prunes to the newest 5 images.

---

## Resources that exist (from `.arn-env`)

| Resource | Name / identifier |
|----------|-------------------|
| App Runner service | `life-planning` (URL `cdpa6wyfze.us-east-1.awsapprunner.com`) |
| App Runner autoscaling | `life-planning-single` (**Min=1, Max=1** — single-writer) |
| App Runner GitHub connection | `life-planning-github` (available, unused) |
| ECR repo | `life-planning` (KMS-encrypted, scan-on-push, prune-to-5) |
| ECR access role | `life-planning-apprunner-ecr-access` |
| Instance role | `life-planning-apprunner-instance` (least-privilege) |
| KMS key | `alias/life-planning` (**single-region** — phase-2 upgrade needed) |
| Admin secret | `life-planning/admin-credentials` |
| JWT secret | `life-planning/jwt-secret` |
| Uploads bucket | `life-planning-uploads-<random>` (private, SSE-KMS, versioned, TLS-only) |
| DB replica bucket | `life-planning-db-<random>` (Litestream target, same hardening) |
| WAF web ACL | `life-planning-waf` (regional, attached to the service) |
| Custom domain | `life-planning.my-deployment.com` (App Runner managed TLS) |
| SNS topic | `life-planning-alerts` (email: <owner-email>, confirmed) |
| Route 53 health check | on `/api/health` |
| CloudWatch alarm | `life-planning-down` → SNS |
| Budget | `life-planning-monthly` ($50/mo → SNS) |

---

## Build order (what was actually done)

### 1. Secrets (Secrets Manager)
Admin credential: a 43-char random password stored as
`{"username","password"}` JSON. JWT: an 86-char random string.
```bash
python3 -c "import secrets,json; open('/tmp/a.json','w').write(json.dumps({'username':'admin','password':secrets.token_urlsafe(32)}))"
aws secretsmanager create-secret --name life-planning/admin-credentials --secret-string file:///tmp/a.json --region us-east-1
shred -u /tmp/a.json
python3 -c "import secrets; open('/tmp/j.txt','w').write(secrets.token_urlsafe(64))"
aws secretsmanager create-secret --name life-planning/jwt-secret --secret-string file:///tmp/j.txt --region us-east-1
shred -u /tmp/j.txt
# -> record ADMIN_SECRET_ARN, JWT_SECRET_ARN in .arn-env
```

### 2. KMS key
```bash
aws kms create-key --description "life-planning" --tags TagKey=project,TagValue=life-planning --region us-east-1
aws kms create-alias --alias-name alias/life-planning --target-key-id <KEY_ID> --region us-east-1
aws kms enable-key-rotation --key-id <KEY_ID> --region us-east-1   # annual rotation ON
# -> record KMS_KEY_ARN in .arn-env.  NOTE: single-region (phase-2 upgrade needed)
```

### 3. S3 buckets (uploads + DB replica)
Random-suffix names (not guessable). For **each** bucket apply: Block Public
Access (all 4), versioning, SSE-KMS default (the key above), a TLS-only bucket
policy (deny `aws:SecureTransport=false`), and a lifecycle rule to expire
noncurrent versions after 60 days.
```bash
set -a; . ./.arn-env; set +a
for B in "$UPLOADS_BUCKET" "$DB_REPLICA_BUCKET"; do
  aws s3api create-bucket --bucket "$B" --region us-east-1
  aws s3api put-public-access-block --bucket "$B" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-versioning --bucket "$B" --versioning-configuration Status=Enabled
  aws s3api put-bucket-encryption --bucket "$B" --server-side-encryption-configuration "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\",\"KMSMasterKeyID\":\"$KMS_KEY_ARN\"},\"BucketKeyEnabled\":true}]}"
  # + TLS-only bucket policy + lifecycle (expire noncurrent 60d)
done
# -> record UPLOADS_BUCKET, DB_REPLICA_BUCKET in .arn-env
```

### 4. Instance role (least-privilege, app assumes this)
Trust: `tasks.apprunner.amazonaws.com`. Inline policy (specific ARNs, **no
wildcards**): `secretsmanager:GetSecretValue` on both secrets;
`s3:Get/Put/Delete/ListBucket` on BOTH buckets (uploads + DB replica);
`kms:Decrypt/Encrypt/GenerateDataKey` on the key.
```bash
# -> record APPRUNNER_ROLE_ARN in .arn-env
```

### 5. ECR repo + first image
```bash
aws ecr create-repository --repository-name life-planning \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS,kmsKey=$KMS_KEY_ARN --region us-east-1
aws ecr put-lifecycle-policy --repository-name life-planning \
  --lifecycle-policy-text '{"rules":[{"rulePriority":1,"description":"keep newest 5","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":5},"action":{"type":"expire"}}]}' --region us-east-1
# -> record ECR_REPO_URI in .arn-env
./deploy/build_push.sh    # builds the Dockerfile, pushes :latest
```

### 6. ECR access role (App Runner pulls the private image)
Trust: `build.apprunner.amazonaws.com`. Attach managed
`AWSAppRunnerServicePolicyForECRAccess` + an inline `kms:Decrypt` on the key
(repo is KMS-encrypted).
```bash
# -> record ECR_ACCESS_ROLE_ARN in .arn-env
```

### 7. App Runner service (from ECR image)
`create-service` with `ImageRepository` (type ECR, `:latest`),
`AutoDeploymentsEnabled=true`, `AccessRoleArn` = ECR access role,
`InstanceRoleArn` = instance role, port 8000, and env vars below.

> **Health-check path = `/api/alive`** (always 200), NOT `/api/health`. App
> Runner gates deployments on this path; `/api/health` is toggleable to 503 for
> failover drills (see PHASE2_FAILOVER.md), so using it here would block deploys.
> Set/confirm with
> `update-service --health-check-configuration Protocol=HTTP,Path=/api/alive,...`.

env vars:
```
DEPLOY_MODE=aws  AWS_REGION=us-east-1
ADMIN_SECRET_ARN=...  JWT_SECRET_ARN=...
UPLOADS_BUCKET=...  DB_REPLICA_BUCKET=...  PRESIGN_TTL_SECONDS=900
```
```bash
# -> record SERVICE_ARN, SERVICE_URL in .arn-env
```

### 7a. Pin autoscaling to a single instance (CRITICAL)
SQLite + Litestream is **single-writer**; >1 instance = silent data corruption
(split-brain). Create a Max=1 config and apply it.
```bash
aws apprunner create-auto-scaling-configuration --auto-scaling-configuration-name life-planning-single \
  --max-concurrency 100 --min-size 1 --max-size 1 --region us-east-1
aws apprunner update-service --service-arn "$SERVICE_ARN" --auto-scaling-configuration-arn <ASC_ARN> --region us-east-1
# -> record AUTOSCALING_ARN in .arn-env
```

### 8. WAF (regional web ACL, attached to the service)
Rules by priority: (0) **Allow** `/api/health` exact-match; (1) rate-based
Block on `/api/auth/login` (limit 100/IP); (2-4) managed CommonRuleSet,
KnownBadInputs, AmazonIpReputationList; (5) **Block** when `Host` contains
`awsapprunner.com` (locks the default domain; custom domain still served).
Within CommonRuleSet, override `SizeRestrictions_BODY` and
`CrossSiteScripting_BODY` to **Count** — otherwise file uploads (>8KB bodies)
are blocked.
```bash
# NOTE: WAF ByteMatch SearchString values must be base64-encoded in the --rules file.
aws wafv2 create-web-acl --name life-planning-waf --scope REGIONAL --region us-east-1 ...
aws wafv2 associate-web-acl --web-acl-arn "$WAF_ACL_ARN" --resource-arn "$SERVICE_ARN" --region us-east-1
# -> record WAF_ACL_ARN in .arn-env
```

### 9. Custom domain + DNS
`associate-custom-domain` returns a CNAME target + 3 ACM validation CNAMEs
(incl. a `www.` one). Write all of them to zone `Z0101762W5VWFT32BT2B` as
UPSERTs; wait for the domain to go `active` (ACM issues managed TLS, ~2 min).
```bash
aws apprunner associate-custom-domain --service-arn "$SERVICE_ARN" --domain-name life-planning.my-deployment.com --region us-east-1
aws apprunner describe-custom-domains --service-arn "$SERVICE_ARN" --region us-east-1   # get CertificateValidationRecords
aws route53 change-resource-record-sets --hosted-zone-id Z0101762W5VWFT32BT2B --change-batch file://batch.json
# -> record CUSTOM_DOMAIN in .arn-env
```

### 10. Alerting + budget
```bash
aws sns create-topic --name life-planning-alerts --region us-east-1
aws sns subscribe --topic-arn <TOPIC> --protocol email --notification-endpoint <owner-email> --region us-east-1  # confirm via email
aws route53 create-health-check ... ResourcePath=/api/health ...
aws cloudwatch put-metric-alarm --alarm-name life-planning-down --namespace AWS/Route53 --metric-name HealthCheckStatus ... --alarm-actions <TOPIC>
aws budgets create-budget --account-id 809784555426 ...  # $50/mo -> SNS
# -> record ALERT_TOPIC_ARN, HEALTHCHECK_ID in .arn-env
```

### 11. Cleanup
Deleted the orphan ACM validation CNAME
`_3cce7ec...app.housing-planner.com` in zone `Z02860032ZNCH6LLUL27W`.

### 12. Cost-allocation tags
All 13 app resources tagged `project=life-planning`; the `project` tag
activated in the Billing console. Route 53 zone intentionally excluded.

---

## Fixes discovered during go-live (baked into the code)

These were real bugs found while deploying — all fixed and committed:

1. **Avatar upload → local disk.** `profiles.py` wrote avatars to the container
   FS instead of S3. Fixed to use the `storage` abstraction (commit:
   "Fix avatar upload to use S3 storage").
2. **Presigned URLs failed on the KMS bucket (SigV2).** KMS-encrypted S3
   requires **SigV4**; boto3 defaulted to SigV2 → images uploaded but wouldn't
   display (HTTP 400 `InvalidArgument`). Pinned the S3 client to
   `signature_version="s3v4"` in `storage.py`.
3. **WAF blocked uploads.** `SizeRestrictions_BODY` (>8KB body) blocked the
   multipart avatar POST → UI hung at "saving". Overrode that rule (and
   `CrossSiteScripting_BODY`) to Count.
4. **Ephemeral DB wiped on every redeploy.** App Runner's filesystem is
   ephemeral → profiles vanished. Added **Litestream** (entrypoint restores the
   SQLite DB from the DB bucket on boot, replicates WAL every 1s). Verified data
   survives redeploys.
5. **Security hardening** (post-review): security-headers middleware
   (CSP/HSTS/X-Frame/nosniff/Referrer), `/docs`+`/openapi` disabled in aws mode,
   CORS locked to the app origin, JWT TTL 24h → 2h.

---

## Operate it

- **Health / status / logs:** `./deploy/monitor.sh {all|status|health|logs|dns|watch|smoke}`
- **Redeploy new code:** `./deploy/build_push.sh` (auto-deploys)
- **Admin password:** `aws secretsmanager get-secret-value --secret-id life-planning/admin-credentials --region us-east-1 --query SecretString --output text`
- **Rollback:** `build_push.sh` stamps a timestamp tag per build; re-point the
  service at a known-good tag (see FOLLOW_UPS for tagging a `:stable`).

---

## Phase 2 (deferred) — second region + failover

us-west-2 standby, S3 CRR, **KMS multi-region key** (blocker — current key is
single-region), Secrets Manager replica, Route 53 health-checked failover,
Litestream continuous replay on the standby, and the dormant
`RegionFailoverBanner` in the SPA. See `DEPLOYMENT_STRATEGY.md` and
`FOLLOW_UPS.md`.
