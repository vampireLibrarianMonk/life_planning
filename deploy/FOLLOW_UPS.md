# Deployment Follow-Ups (Deferred Items)

Reference list of work intentionally deferred after the phase-1 go-live and the
adversarial review on 2026-10-20. Nothing here is blocking; the live app is
hardened and data is durable. Ordered roughly by value.

Live app: https://life-planning.my-deployment.com (App Runner, us-east-1)
Resource IDs: see git-ignored `.arn-env`.

---

## Action required by owner (not code)

- [ ] **Confirm the SNS alert email.** A confirmation email was sent to
      `<owner-email>` (subject "AWS Notification - Subscription
      Confirmation"). Click **Confirm subscription** or the `life-planning-down`
      CloudWatch alarm cannot notify you. Verify with:
      `aws sns list-subscriptions-by-topic --topic-arn <ALERT_TOPIC_ARN> --region us-east-1`
      (status should become `confirmed`).
- [ ] **Store admin password + AWS recovery off the deploy laptop.** Deploys
      require local Docker + AWS creds on one machine; that laptop is a single
      operational point of failure. Keep the Secrets Manager admin password and
      a way into AWS somewhere else safe.

---

## This week

- [ ] **Manual secret-rotation drill (proves the kill switch).** Rotate both
      `life-planning/admin-credentials` and `life-planning/jwt-secret` once by
      updating the secret value and restarting/redeploying the service, then
      confirm login still works. Rotating the JWT secret instantly invalidates
      all outstanding tokens — a useful "log everyone out" lever. Document the
      runbook: *update secret → redeploy → done.*
- [ ] **Tag a `:stable` ECR image for guaranteed rollback.** Auto-deploy ships
      `:latest` straight to the single instance with no staging. `build_push.sh`
      already stamps a timestamp tag; additionally tag a known-good image
      `:stable` so a bad deploy can be rolled back by pointing the service at
      `:stable`. Document the rollback command.
- [ ] **Independent daily DB snapshot (separate from Litestream).** Litestream
      is *replication*, not *backup* — it faithfully propagates a bad delete or
      corruption within ~1s. Add a daily timestamped copy of the SQLite replica
      to a separate S3 prefix/bucket with ~30-day retention for point-in-time
      recovery. (S3 versioning on the DB bucket partially covers this already.)
- [ ] **Run the redeploy-survival drill explicitly once.** We proved data
      survived multiple real redeploys tonight, but formalize it: write a
      sentinel record, force a new deployment, confirm the sentinel + existing
      data are present AND the entrypoint log shows `restore` ran (not a fresh
      empty DB). Keep as a periodic check.
- [ ] **Read the ECR image scan results once.** Scan-on-push is enabled; pull
      findings for the current image and triage any HIGH/CRITICAL. Consider
      pinning the App Runner image to a digest instead of `:latest` so you know
      exactly what is deployed.

---

## Phase 2 (only if/when dual-region is actually wanted)

> Decision so far: single-region is the right call for a single-family app.
> Do NOT half-build dual-region — half-built failover is worse than none.
> These are the prerequisites IF phase 2 is ever pursued.

- [ ] **Upgrade KMS key to multi-region.** The current CMK
      (`alias/life-planning`) is single-region. A us-west-2 standby cannot
      decrypt the replicated S3 data without a multi-region key (same key
      id/material, policy valid in both regions). Recreate as MRK + re-encrypt,
      or add a replica. This is the known blocker for phase 2.
- [ ] **Second region bring-up:** standby App Runner service (warm, min=1),
      S3 Cross-Region Replication for uploads + DB buckets, Secrets Manager
      replica in us-west-2, Route 53 health-checked failover records, Litestream
      continuous replay on the standby.
- [ ] **Wire the region-failover banner.** `RegionFailoverBanner.jsx` is built
      and mounted but dormant; it activates once a standby exists.
- [ ] **Quarterly failover game-day** (the release gate described in
      `DEPLOYMENT_STRATEGY.md`): force a primary health failure, confirm
      automated failover, RTO <= 5 min, RPO <= 60s, standby decrypts with
      west-region keys, WAF did not block the health checker.

---

## Accept / documented (no action planned)

- **Single region (us-east-1).** Downtime from a regional outage is tolerable
  for a family app; versioning + Litestream are the recovery story.
- **~1s RPO write-loss window** if the container dies mid-write before the WAL
  ships. Negligible and re-enterable for this workload.
- **App Runner min-1 always-on cost** (~$5-15/mo) — inherent to always-on.
- **KMS CMK + double-bucket versioning** — mild over-build (~$1-3/mo); only
  downgrade to SSE-S3 if trimming cost further later.
- **Manual laptop deploys, no CI/CD** — reasonable at this scale; do not add CI.
- **WAF (~$5-6/mo + rules)** — kept as login brute-force defense and the
  default-domain lock. Trim to a single rate rule only if cost becomes a concern.
- **Dormant `child` / `readonly` roles** — exist in the model with backend
  guards but are not wired into the UI; untested until enabled.

---

## Security posture snapshot (as of 2026-10-20, post-review)

Fixed and verified live: security headers (CSP/HSTS/X-Frame/nosniff/Referrer),
`/docs`+`/openapi` disabled in aws mode, CORS locked to own origin, JWT TTL 2h,
App Runner MaxSize=1 (no split-brain), KMS rotation on, S3 noncurrent-version
lifecycle (60d), Route 53 health check + CloudWatch alarm -> SNS, $50/mo budget
alert. WAF (login rate-limit + managed groups + default-domain 403). Private
KMS-encrypted S3 (BPA, versioned, TLS-only). Least-privilege task roles;
workloads never use the `house-user` long-lived keys.
