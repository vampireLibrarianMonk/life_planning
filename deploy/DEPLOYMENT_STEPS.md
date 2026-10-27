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
| SNS topic | `life-planning-alerts` (email: `pmflani@gmail.com`, confirmed 2026-10-27) |
| Route 53 health check | east `/api/health` + west `/api/health` (failover pair) |
| CloudWatch alarms | `life-planning-east` + `life-planning-west` (HealthCheckStatus) → SNS |
| Budget | `life-planning-monthly` ($70/mo → SNS) |

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
aws sns subscribe --topic-arn <TOPIC> --protocol email --notification-endpoint pmflani@gmail.com --region us-east-1  # confirm via email
aws route53 create-health-check ... ResourcePath=/api/health ...   # one per region (east primary, west standby)
# Two state-neutral alarms so a RECOVERY email never says "down":
#   life-planning-east  (us-east-1 PRIMARY)  ALARM=down / OK=back up
#   life-planning-west  (us-west-2 STANDBY)  ALARM=down / OK=up
aws cloudwatch put-metric-alarm --alarm-name life-planning-east --namespace AWS/Route53 --metric-name HealthCheckStatus \
  --dimensions Name=HealthCheckId,Value=<EAST_HC> --statistic Minimum --period 60 --evaluation-periods 2 \
  --threshold 1 --comparison-operator LessThanThreshold --treat-missing-data breaching \
  --alarm-actions <TOPIC> --ok-actions <TOPIC>
aws cloudwatch put-metric-alarm --alarm-name life-planning-west --namespace AWS/Route53 --metric-name HealthCheckStatus \
  --dimensions Name=HealthCheckId,Value=<WEST_HC> --statistic Minimum --period 60 --evaluation-periods 2 \
  --threshold 1 --comparison-operator LessThanThreshold --treat-missing-data breaching \
  --alarm-actions <TOPIC> --ok-actions <TOPIC>
aws budgets create-budget --account-id 809784555426 ...  # $70/mo -> SNS
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

## Email (Amazon SES) — account invitations

New-user invitations (one-time, 72h "set your password" links) are sent by the
**local `provision_user.py` CLI** via Amazon SES. The running web app never
sends email, so there's no public email-send surface.

### What exists (both regions — east primary, west failover)
| Thing | Value |
|-------|-------|
| Sender ("project") | SES **Configuration Set** `life-planning` (tag `project=life-planning`) |
| **From address** | `no-reply@life-planning.my-deployment.com` (domain-authenticated) |
| Verified identity | **DOMAIN** `life-planning.my-deployment.com` (Easy DKIM, RSA-2048) |
| Custom MAIL FROM | `mail.` (east) / `mail-west.` (west) `.life-planning.my-deployment.com` |
| Production access | **enabled** in us-east-1 **and** us-west-2 (out of the SES sandbox) |
| DMARC reports | `rua` → the Proton mailbox (report target only, never a From) |

All IDs are recorded in `.arn-env` (`SES_*`).

### Why we send From the **domain**, not `@proton.me` (the bounce we hit)
Outlook/Hotmail rejected invites sent `From: no-reply-life-planning@proton.me`
with `550 5.7.515 ... DMARC=Fail` — even though SPF and DKIM individually
*passed*. The reason is **DMARC alignment**:

- **SPF** checks the server/envelope sender; **DKIM** is a cryptographic
  signature on the message. Sending through SES makes those pass for
  *amazonses.com*, not for *proton.me*.
- **DMARC** requires the SPF/DKIM-authenticated domain to **align with the
  visible `From:` domain**. Amazon's signature doesn't align with `proton.me`,
  and Proton publishes a strict DMARC policy, so strict receivers reject it.
- You cannot make SES DKIM-sign as `@proton.me` (you don't control Proton's DNS).

**Fix:** authenticate a domain **you** control. We own `my-deployment.com` in
Route 53, so we verified `life-planning.my-deployment.com` in SES and send from
it → SPF **and** DKIM align with our own domain → DMARC passes at Outlook,
Gmail, Yahoo.

### What "Easy DKIM" actually did (so you can read up later)
1. `sesv2 create-email-identity --email-identity life-planning.my-deployment.com
   --dkim-signing-attributes NextSigningKeyLength=RSA_2048_BIT` — SES generated a
   DKIM key pair and returned **3 CNAME tokens**. (SES keeps the private key and
   signs outbound mail; you publish the public half via DNS. 3 records = key
   rotation headroom.)
2. Published the 3 CNAMEs in Route 53:
   `<token>._domainkey.life-planning.my-deployment.com → <token>.dkim.amazonses.com`.
   SES polls DNS; once it sees them, DKIM status → `SUCCESS` and the identity is
   `VerifiedForSending`. **DKIM tokens are per-region**, so east and west each
   have their own 3 CNAMEs (6 total).
3. **Custom MAIL FROM** (`put-email-identity-mail-from-attributes`) + an **MX**
   (`feedback-smtp.<region>.amazonses.com`) and **SPF TXT**
   (`v=spf1 include:amazonses.com ~all`) on the MAIL FROM subdomain → this gives
   **SPF alignment** on our domain. Each region needs its own MAIL FROM
   subdomain + region-specific MX (`mail.` east, `mail-west.` west) because an MX
   can only point at one region's endpoint.
4. A **DMARC policy** TXT at `_dmarc.life-planning.my-deployment.com`
   (`v=DMARC1; p=none; rua=mailto:...; adkim=s; aspf=s`). `p=none` = monitor
   only (mail still delivers because SPF+DKIM align); tighten to `p=quarantine`
   or `p=reject` later once reports look clean.

Further reading: AWS "Easy DKIM" + "Custom MAIL FROM domain" docs; RFC 7489
(DMARC); dmarc.org "how DMARC works" (alignment).

### Production access (leaving the SES sandbox)
Filed with `sesv2 put-account-details --production-access-enabled
--mail-type TRANSACTIONAL ...` per region (AWS reviews manually, ~24h). Check:
```bash
aws sesv2 get-account --region us-east-1 --query 'ProductionAccessEnabled'   # true = out of sandbox
```
It's **per account + per region** (no "project" scope). In the sandbox you can
only send to *verified* recipients; in production you can send to anyone, so we
request it for **both** regions (failover must be able to email too).

### Send an invitation
```bash
export SES_SENDER="no-reply@life-planning.my-deployment.com"   # NEVER an @proton.me From
export AWS_REGION=us-east-1
export ADMIN_USERNAME=... ADMIN_PASSWORD=...   # from Secrets Manager
.venv-test/bin/python app/backend/provision_user.py \
  --type visitor --username <user> --display-name "<Name>" \
  --email <addr> --app-url https://life-planning.my-deployment.com --expires-hours 72
```
Friendly `--type`: father/mother→admin, visitor→readonly, child→child (with
`--issue-child-login --child-write`). The email states the role, what the app
is, and the 72h expiry; no password is ever emailed or stored.

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
