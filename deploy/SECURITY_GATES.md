# Security Confirmation Gates — Phase 1 Deployment

A per-step "what are we doing / why is it secure / prove it" companion to
`DEPLOYMENT_STEPS.md` and `GO_LIVE_CHECKLIST.md`.

**Rule for this deployment:** we do not advance to the next step until its
**Verify** command confirms the security control is actually in place. Every
step below is paired with (1) what the action does, (2) the security property
it establishes, and (3) the exact command that proves it.

Nothing here has been run yet — these are the gates we will walk together.

---

## Step 1 — JWT signing secret (Secrets Manager)

- **Doing:** store a 64-char random JWT secret in Secrets Manager.
- **Secure because:** the signing secret never lives in the repo, the image,
  or an env literal — the app reads it at boot via its IAM role. Rotating the
  secret invalidates forged tokens.
- **Verify:**
  ```bash
  aws secretsmanager describe-secret --secret-id life-planning/jwt-secret \
    --region us-east-1 --query '{Name:Name,Rotation:RotationEnabled}'
  # And prove it is NOT world-readable: the value is only fetched later by the
  # App Runner role, never printed here.
  ```

## Step 2 — KMS key

- **Doing:** create a customer-managed KMS key + alias `alias/life-planning`.
- **Secure because:** uploads (children's PII) and the DB stream are encrypted
  at rest under a key whose use we control and can audit in CloudTrail. (Phase 2
  converts this to a multi-region key so the standby can decrypt.)
- **Verify:**
  ```bash
  aws kms describe-key --key-id alias/life-planning --region us-east-1 \
    --query 'KeyMetadata.{State:KeyState,Manager:KeyManager,MultiRegion:MultiRegion}'
  # Expect: State=Enabled, Manager=CUSTOMER.
  ```

## Step 3 — Uploads S3 bucket

- **Doing:** private bucket with Block Public Access, versioning, SSE-KMS
  default, and a TLS-only bucket policy.
- **Secure because:** no object is ever publicly reachable; every object is
  encrypted with our KMS key; plaintext (non-HTTPS) access is denied; versioning
  protects against accidental/malicious overwrite.
- **Verify (all four must pass):**
  ```bash
  set -a; . ./.arn-env; set +a; B="$UPLOADS_BUCKET"
  aws s3api get-public-access-block --bucket $B \
    --query 'PublicAccessBlockConfiguration'      # all four = true
  aws s3api get-bucket-encryption --bucket $B \
    --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault'  # aws:kms
  aws s3api get-bucket-versioning --bucket $B --query 'Status'   # Enabled
  aws s3api get-bucket-policy --bucket $B --query 'Policy' \
    | grep -q SecureTransport && echo "TLS-only policy present"
  ```

## Step 4 — App Runner instance role (least privilege)

- **Doing:** an IAM role trusted only by App Runner, granting the minimum:
  read the two secret ARNs, R/W only the uploads bucket prefix, use only the
  one KMS key, write its own logs.
- **Secure because:** no wildcards, no `s3:*`, no access to anything else in the
  account; the workload never uses the long-lived `house-user` keys.
- **Verify:**
  ```bash
  ROLE=<role-name>
  aws iam list-attached-role-policies --role-name $ROLE
  aws iam get-role --role-name $ROLE \
    --query 'Role.AssumeRolePolicyDocument.Statement[0].Principal'  # apprunner
  # Eyeball each inline policy: resources are specific ARNs, not "*".
  ```

## Step 5 — App Runner service

- **Doing:** build from GitHub via Dockerfile; run on :8000; env `DEPLOY_MODE=aws`
  + the ARNs/bucket; attach the role from step 4; health check `/api/health`.
- **Secure because:** managed compute (no SSH, no host to patch); the app's own
  guard **refuses to start if the admin credential is still the default**, so it
  can never be exposed with admin/changeme; secrets arrive only via the role.
- **Verify:**
  ```bash
  ./deploy/monitor.sh watch     # settles to RUNNING (not CREATE_FAILED)
  ./deploy/monitor.sh health    # expect mode:aws, correct region, bucket set
  # Confirm the default-cred guard is live: logs must NOT show the service
  # serving with admin/changeme (it would RuntimeError at startup instead).
  ./deploy/monitor.sh logs | grep -i "refusing to start" || echo "guard not tripped (good: real secret in use)"
  ```

## Step 6 — AWS WAF (regional web ACL)

- **Doing:** rate-based rule on the login path + managed CommonRuleSet,
  KnownBadInputs, IpReputation; `/api/health` allow-listed above the rules.
- **Secure because:** blunts credential-stuffing/brute force on the internet-
  facing admin login and common exploit patterns, without blocking the Route 53
  health checker.
- **Verify:**
  ```bash
  aws wafv2 get-web-acl --scope REGIONAL --region us-east-1 \
    --name <acl> --id <id> --query 'WebACL.Rules[].Name'
  aws wafv2 list-resources-for-web-acl --web-acl-arn <acl-arn> --region us-east-1
  # Confirm the service ARN is listed (ACL actually attached).
  ```

## Step 7 — Custom domain + TLS

- **Doing:** attach `life-planning.my-deployment.com`; add validation + alias
  records to Route 53; App Runner issues managed TLS.
- **Secure because:** traffic is HTTPS end-to-end with an AWS-managed cert whose
  private key never leaves AWS; HSTS is set at the app layer.
- **Verify:**
  ```bash
  ./deploy/monitor.sh dns        # domain Active, cert issued, TLS verify = 0
  curl -sI https://life-planning.my-deployment.com | grep -i strict-transport-security
  ```

## Step 8 — Live verification

- **Doing:** end-to-end check as a user.
- **Secure because:** proves the real login uses the strong secret, uploads are
  encrypted + presigned (not public), and the mode is `aws`.
- **Verify:**
  ```bash
  ./deploy/monitor.sh all
  ./deploy/monitor.sh smoke      # Playwright walkthrough vs the live URL
  # Manual: log in with the Secrets Manager password; upload a file and confirm
  # /api/uploads/<key> 307-redirects to a presigned S3 URL (not a public object).
  curl -sI "https://life-planning.my-deployment.com/api/uploads/<key>" | grep -i location
  ```

## Step 9 — Cleanup

- **Doing:** remove the orphan `app.housing-planner.com` validation CNAME.
- **Secure because:** removes a stale, unused DNS record (reduces confusion /
  attack surface); it is unrelated to this deployment.

---

## Standing security confirmations (true the whole time)

- No secret value is ever echoed to the terminal or committed — only ARNs.
- The database is never publicly reachable (SQLite is on the instance; no public
  datastore exists in phase 1).
- The workload uses a scoped IAM role, never the long-lived `house-user` keys.
- Every destructive or account-affecting action will be shown to you for
  explicit confirmation before it runs.
