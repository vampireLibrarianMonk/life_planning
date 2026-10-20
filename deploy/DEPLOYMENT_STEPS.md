# Deployment Steps — Phase 1 (single region, us-east-1)

Succinct, ordered steps to take the Life Plan Tracker online at
`https://life-planning.my-deployment.com` via AWS App Runner. Run **after** the
hardened code is pushed to GitHub (App Runner builds from the repo).

Prereqs: AWS creds active (IAM user `house-user`, account `809784555426`),
`DEPLOY_MODE=aws` image builds from the root `Dockerfile`, domain
`my-deployment.com` in Route 53 (zone `Z0101762W5VWFT32BT2B`).

Already provisioned:
- Admin credential secret:
  `arn:aws:secretsmanager:us-east-1:809784555426:secret:life-planning/admin-credentials-dPvvor`

> **ARN convention:** every step that creates a resource prints an ARN/ID.
> **Record each one in the git-ignored `.arn-env` file** immediately, then
> source it (`set -a; . ./.arn-env; set +a`) so later steps and
> `monitor.sh` reference resources by variable, never by a hardcoded value.
> `.arn-env` is the single source of truth for this deployment's resources.

---

## 1. JWT secret (Secrets Manager)

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))" > /tmp/jwt.txt
aws secretsmanager create-secret \
  --name life-planning/jwt-secret \
  --secret-string "file:///tmp/jwt.txt" \
  --region us-east-1
shred -u /tmp/jwt.txt
# -> record ARN as JWT_SECRET_ARN in .arn-env
```

## 2. KMS key (single-region now; convert to multi-region in phase 2)

```bash
aws kms create-key --description "life-planning uploads" \
  --region us-east-1 --query KeyMetadata.KeyId --output text
aws kms create-alias --alias-name alias/life-planning \
  --target-key-id <KEY_ID> --region us-east-1
# -> record the key ARN as KMS_KEY_ARN in .arn-env (NOTE: single-region for phase 1)
```

## 3. Uploads bucket (private, encrypted, versioned)

```bash
# Bucket name uses a securely-random suffix (not the account id) so it is not
# guessable. The real name lives in .arn-env; source it:
set -a; . ./.arn-env; set +a
aws s3api create-bucket --bucket "$UPLOADS_BUCKET" --region us-east-1
aws s3api put-public-access-block --bucket "$UPLOADS_BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$UPLOADS_BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$UPLOADS_BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"alias/life-planning"}}]}'
# Add a TLS-only bucket policy (deny aws:SecureTransport=false).
```

## 4. IAM role for App Runner (instance role, least privilege)

Trust policy: `tasks.apprunner.amazonaws.com`. Permissions (scoped to ARNs):
- `secretsmanager:GetSecretValue` on the admin + jwt secret ARNs
- `s3:GetObject,PutObject,DeleteObject` on `arn:aws:s3:::$UPLOADS_BUCKET/*`
- `kms:Decrypt,Encrypt,GenerateDataKey` on the KMS key ARN

## 5. App Runner service (builds from GitHub)

1. App Runner console → Create service → Source = GitHub → connect the repo/branch.
2. Build: use the root `Dockerfile` (Managed build or Dockerfile).
3. Port: `8000`. Health check path: `/api/health`.
4. Instance role: the role from step 4.
5. Environment variables:
   | Key | Value |
   |-----|-------|
   | `DEPLOY_MODE` | `aws` |
   | `AWS_REGION` | `us-east-1` |
   | `ADMIN_SECRET_ARN` | `...:life-planning/admin-credentials-dPvvor` |
   | `JWT_SECRET_ARN` | *(from step 1)* |
   | `UPLOADS_BUCKET` | *(from `.arn-env` — random-suffix name)* |
   | `PRESIGN_TTL_SECONDS` | `900` |
6. Deploy. Note the service's `*.awsapprunner.com` URL.

## 6. Attach WAF (regional web ACL)

```bash
# Create a regional web ACL (us-east-1) with: rate-based login rule +
# AWSManagedRulesCommonRuleSet + KnownBadInputs + AmazonIpReputationList.
# Allow-list /api/health above the rules.
aws wafv2 associate-web-acl \
  --web-acl-arn <WEB_ACL_ARN> \
  --resource-arn <APP_RUNNER_SERVICE_ARN> \
  --region us-east-1
```

## 7. Custom domain + DNS

1. App Runner → the service → Custom domains → add
   `life-planning.my-deployment.com`. App Runner returns DNS validation
   (CNAME) records and the target.
2. Add those validation CNAMEs **and** the alias/CNAME for
   `life-planning.my-deployment.com` → the App Runner domain in Route 53 zone
   `Z0101762W5VWFT32BT2B`.
3. Wait for App Runner to issue its managed TLS cert and the domain to go
   Active.

## 8. Verify

```bash
curl -s https://life-planning.my-deployment.com/api/health   # {"status":"ok","config":{"mode":"aws",...}}
# Log in with the admin password from Secrets Manager:
aws secretsmanager get-secret-value --secret-id life-planning/admin-credentials \
  --region us-east-1 --query SecretString --output text
```
- Confirm login works, an attachment upload round-trips through S3, and
  `mode` reads `aws` in `/api/health`.

## 9. Cleanup

- Delete the orphan validation CNAME `_3cce7ec...app.housing-planner.com`
  in zone `Z02860032ZNCH6LLUL27W` (leftover from a prior attempt; unrelated).

---

## Phase 2 (deferred) — second region + failover

us-west-2 standby, S3 CRR, KMS multi-region key, Secrets Manager replica,
Route 53 health-checked failover, Litestream continuous replay, and the
client-side region-changeover countdown. See `DEPLOYMENT_STRATEGY.md`.
