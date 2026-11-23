# Deployment Follow-Ups (Deferred Items)

Reference list of work intentionally deferred after the phase-1 go-live and the
adversarial review on 2026-10-20. Nothing here is blocking; the live app is
hardened and data is durable. Ordered roughly by value.

Live app: https://life-planning.my-deployment.com (App Runner, us-east-1)
Resource IDs: see git-ignored `.arn-env`.

---

## Action required by owner (not code)

- [x] **Confirm the SNS alert email.** Confirmed for `pmflani@gmail.com`
      (2026-10-27) — the `life-planning-east` / `life-planning-west` alarms
      now notify on both DOWN and recovery (state-neutral names so a recovery
      email never says "down").
- [x] **Cost-allocation tagging.** All Life Plan resources tagged
      `project=life-planning` (Route 53 hosted zone excluded as shared infra).
      The `project` user-defined cost-allocation tag was activated in the
      Billing console on 2026-10-20. **Re-audited 2026-10-29** after the Phase 2
      dual-region expansion: tagged 3 resources created later that had been
      missed — the us-west-2 WAF ACL (`life-planning-waf`) and the two
      CloudWatch alarms (`life-planning-east`, `life-planning-west`). Full set
      now consistent (both App Runner services, 4 S3 buckets, 4 secrets, both
      KMS MR keys, both WAF ACLs, SNS, CRR role, both autoscaling configs, ECR,
      both IAM roles, both Route 53 health checks).
- [x] **Isolated cost (checked 2026-10-29).** Cost Explorer filtered by
      Tag → `project=life-planning`: steady-state **~$1.11/day ≈ $33/mo**
      (MTD Oct 1–29 = $9.58). This is ABOVE the earlier ~$20–27/mo estimate
      because that predated the dual-region build — the delta is the second
      App Runner instance + a second WAF ACL (~$9/mo each for WAF). MTD split:
      App Runner $4.75, WAF $3.06, KMS $0.72, Secrets $0.57, Route 53 $0.43,
      S3 $0.04, ECR $0.01, SNS $0. Still well within the $70/mo budget cap.
      (Sept = $0: the tag/deploy predate it, not real savings.)
- [ ] **Store admin password + AWS recovery off the deploy laptop.** Deploys
      require local Docker + AWS creds on one machine; that laptop is a single
      operational point of failure. Keep the Secrets Manager admin password and
      a way into AWS somewhere else safe.

---

## This week

- [x] **Development-goals PDF evidence appendix (implemented, 2026-11-23).**
      Upgrade the current browser-printed age-band checklist into a two-part
      family record: keep the complete checklist first, then add a bounded
      evidence appendix. Evidence is **opt-in**, not automatically selected:
      add `featured_for_print` and `print_order` to the existing
      `MediaObjectiveLink` relationship and allow at most **two photos and one
      video per objective**. Add a Gallery-to-goal picker in both useful
      directions: let an objective select existing Gallery media, and let a
      Gallery item's actions select one or more development goals. Reuse the
      canonical `ProfileMedia` object through `MediaObjectiveLink`; do not copy,
      move, or re-upload the file. Add exact-content duplicate prevention for
      all upload paths, including direct/multipart videos: persist a SHA-256 for
      every upload and, before a transfer, look only within that child's active
      Gallery for a matching hash. If a match exists, make **Use existing
      evidence** (and link it to the selected goal) the only matching-file
      action, and handle a match already linked to that goal without creating a
      second link. Do not trust a browser-supplied hash by itself: confirm it
      against the completed object's provider/object checksum before marking a
      direct upload ready. Enforce the active `(profile_id, sha256)` invariant
      server-side to close concurrent-upload races while preserving soft-delete
      semantics; never reveal a duplicate or hash match across profiles. Show
      an omitted-item count linking the reader back
      to the in-app Gallery. Do not embed playable video or original-size media
      in the PDF; render photos as bounded preview derivatives, and render each
      selected video as a static cover/poster card with title, date, caption,
      and a QR/deep link to the authenticated app. The link must be a stable,
      login-protected objective/Gallery URL — never an S3 object key,
      presigned URL, share token, or public media URL (presigned Gallery GET
      URLs expire after one hour). Prompt for/use the existing observation as a
      visible caption. Add a bulk, authorized print-evidence API for an age
      band (avoid one request per objective), print CSS with page-break-safe
      evidence cards, a child-data print warning, and tests for limits,
      captions, output page/file-size budgets, deep-link authorization,
      cross-profile denial, omitted counts, and absence of S3 URLs in the
      generated document. For a first release, require a user-selected cover
      photo for videos rather than adding FFmpeg to App Runner; evaluate a
      thumbnail service/Lambda only if automatic video posters become needed.
      **Test status (2026-11-23):** implemented and covered by
      `app/frontend/tests/development_goals_pdf.spec.js` and backend Gallery
      tests. Chromium creates a real PDF with deterministic, non-personal
      fixtures: two selected photos, one selected video represented only by a
      parent-selected cover photo, caption/date/title, and a third linked image
      omitted with a visible count. The tests enforce the two-photo/one-video
      server-side cap, no playable `<video>` or original-size image in print,
      authenticated app deep links only, page/file budgets, cross-profile
      denial, and no object/presigned URLs. Fixtures are generated in tests;
      no real family media or deployed environment is used.

- [ ] **Manual secret-rotation drill (proves the kill switch).** Rotate both
      `life-planning/admin-credentials` and `life-planning/jwt-secret` once by
      updating the secret value and restarting/redeploying the service, then
      confirm login still works. Rotating the JWT secret instantly invalidates
      all outstanding tokens — a useful "log everyone out" lever. Document the
      runbook: *update secret → redeploy → done.*
- [x] **Rollback via immutable digest (DONE 2026-10-31, supersedes `:stable`).**
      The old plan (a movable `:stable` tag) is **incompatible with the now-
      IMMUTABLE ECR repo** and with the digest-promote deploy model. Rollback is
      now `./deploy/promote.sh <known-good-timestamp-tag>`, which resolves that
      tag's immutable digest and `update-service`s both regions. No mutable tag.
- [ ] **Independent daily DB snapshot (separate from Litestream).** Litestream
      is *replication*, not *backup* — it faithfully propagates a bad delete or
      corruption within ~1s. Add a daily timestamped copy of the SQLite replica
      to a separate S3 prefix/bucket with ~30-day retention for point-in-time
      recovery. (S3 versioning on the DB bucket partially covers this already.)
- [x] **DB cross-region replication repair (2026-11-23).** Object Lock is
      enabled on the East and West database buckets, but the `life-planning-s3-crr`
      role lacked the required source reads `s3:GetObjectRetention` and
      `s3:GetObjectLegalHold`. S3 marked DB objects after 03:55 UTC as `FAILED`;
      the two least-privilege permissions were added to the existing role, and
      S3 Batch Replication job `f865f310-da1b-4ad8-bebf-12498cb278ce` backfilled
      all **458/458** failed DB objects with zero task failures. A newly written
      Litestream segment and a formerly failed historical segment both now show
      `COMPLETED` in East and `REPLICA` in West. The independent daily snapshot
      follow-up above remains necessary for point-in-time recovery.
- [ ] **Run the redeploy-survival drill explicitly once.** We proved data
      survived multiple real redeploys tonight, but formalize it: write a
      sentinel record, force a new deployment, confirm the sentinel + existing
      data are present AND the entrypoint log shows `restore` ran (not a fresh
      empty DB). Keep as a periodic check.
- [ ] **Read the ECR image scan results once.** Scan-on-push is enabled; pull
      findings for the current image and triage any HIGH/CRITICAL. (Digest
      pinning is already DONE 2026-10-31 — the service runs a specific immutable
      digest, not `:latest`, and CI runs a Trivy scan on every build.)

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
