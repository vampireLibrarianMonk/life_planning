# Phase 2 — Dual-Region Failover (us-east-1 primary → us-west-2 standby)

Extends the live single-region deployment (see `DEPLOYMENT_STEPS.md`) to an
active/passive two-region setup with automated Route 53 failover. Decided:
**Option 1 — one KMS multi-region key** (re-encrypt the small existing dataset),
full build, failover flipped last so the live app is never at risk mid-build.

- **Primary:** us-east-1 (active, existing)
- **Standby:** us-west-2 (warm; App Runner min=1, Litestream continuous replay)
- **Model:** active/passive, single-writer (SQLite + Litestream). Only ONE region
  writes at a time — DNS failover is the switch. No active/active (would corrupt
  SQLite).
- **Targets:** RTO ~90–150s (Route 53 health-checked DNS failover), RPO ~5s
  (Litestream 1s sync + replication lag).

New resource IDs get recorded in `.arn-env` (suffix `_WEST` for standby twins).

---

## The KMS decision (Option 1) and why it leads

A single-region key cannot be converted, and the us-west-2 standby must decrypt
the replicated S3 data in-region. So we create a **KMS multi-region key**
(primary in us-east-1 + replica in us-west-2, same key id/material) and move the
existing buckets' data under it. Because the dataset is tiny (one profile, a few
avatars, the SQLite replica), re-encryption is a quick copy, not a migration.

> If the dataset were large, Option 2 (separate per-region keys + CRR
> re-encrypt) would avoid touching primary data — but here Option 1 is clean.

---

## Build order (failover flipped LAST)

> **Progress:** Steps 1–7 DONE & verified (2026-10-21). MRK in both regions;
> data re-encrypted; west S3 buckets + CRR (backfilled); secrets replicated to
> west; ECR registry replication; west App Runner `life-planning-west`
> (`kwc6vqrvy9.us-west-2.awsapprunner.com`) RUNNING, MaxSize=1. **Verified: the
> west standby restored the DB from the west replica and serves "Robert
> Flanigan" — full cross-region chain works.** Step 8 (Route 53 failover) is the
> only remaining step and is the one that changes live routing.

> **⚠️ Split-brain / fail-back caveat to resolve in Step 8 design:** both
> services run Litestream. CRR writes east→west into the DB bucket while the
> west service's own Litestream also owns a generation there. In strict
> active/passive this is fine as long as only the routed region takes writes,
> but fail-BACK (west→east) needs a defined reconciliation path. Document the
> replication direction explicitly and treat the standby as read-until-promoted
> in the game-day.

### 1. KMS multi-region key
- Create an MRK in us-east-1 (`--multi-region`), alias `alias/life-planning-mr`.
- Replicate it to us-west-2 (`replicate-key`), same alias there.
- Enable rotation on the primary.
- Record `KMS_MR_KEY_ARN` (east) and `KMS_MR_KEY_ARN_WEST`.

### 2. Re-encrypt existing primary data under the MRK
- Set each primary bucket's default encryption to the MRK.
- `aws s3 cp s3://bucket s3://bucket --recursive --sse aws:kms --sse-kms-key-id <MRK>`
  (rewrites objects under the new key). Tiny dataset → seconds.
- Update the App Runner instance-role policy to allow the MRK (keep old key
  grant until retired).

### 3. Standby S3 buckets (us-west-2)
- Create `life-planning-uploads-<rand>-west` and `life-planning-db-<rand>-west`.
- Same hardening: Block Public Access, versioning, SSE-KMS (us-west-2 MRK
  replica), TLS-only policy, 60-day noncurrent lifecycle.

### 4. Cross-Region Replication (CRR), both buckets east→west
- Enable versioning (already on). Create an IAM **replication role** scoped to
  the source/dest buckets + both KMS keys (decrypt east, encrypt west replica).
- Put a replication config on each primary bucket → its west twin, with
  `SourceSelectionCriteria` for SSE-KMS objects and `EncryptionConfiguration`
  pointing at the west MRK replica.
- Backfill existing objects (CRR only copies new writes): one-time
  `aws s3 cp --recursive` east→west, or S3 Batch Replication.

### 5. Secrets Manager replica (us-west-2)
- `replicate-secret-to-regions` for both `life-planning/admin-credentials` and
  `life-planning/jwt-secret` → us-west-2, encrypted with the west MRK replica.
- Standby app reads the replica in-region (no cross-region call on failover).

### 6. ECR access from us-west-2
- App Runner in us-west-2 needs to pull the image. ECR is regional; either
  enable **ECR cross-region replication** (registry replication rule → us-west-2)
  so `:latest` mirrors west, or point the west service at the east repo via a
  pull-through/again-tagged image. Prefer registry replication (automatic).
- Create west twins of the instance role + ECR access role (IAM is global, but
  policies must reference west bucket/KMS ARNs).

### 7. Standby App Runner service (us-west-2)
- Same image, `DEPLOY_MODE=aws`, env pointing at the **west** buckets + west
  secret ARNs + `AWS_REGION=us-west-2`. Min=1 (warm), MaxSize=1 (single-writer).
- Entrypoint runs Litestream in **continuous replay/restore** against the west
  DB bucket so its SQLite copy stays current from the replicated WAL.
- Attach a us-west-2 regional WAF web ACL (mirror of the east rules).
- Record `SERVICE_ARN_WEST`, `SERVICE_URL_WEST`.

### 8. Route 53 failover (the switch — do LAST)
- Convert `life-planning.my-deployment.com` from a simple record to a
  **failover pair**:
  - PRIMARY → east App Runner domain, associated with the existing
    `/api/health` health check (`life-planning-down`).
  - SECONDARY → west App Runner domain (+ its own health check).
- Add the west domain as an App Runner custom domain first (ACM cert in west) so
  the SECONDARY target is valid before the record flips.
- Activate the `RegionFailoverBanner` (already built, dormant) — it already
  polls `/api/health` and shows the "switching region" overlay.

---

## Failover TEST procedure (game-day)

The point of phase 2 — prove failover actually works, on demand, without losing
data. Run this as a scheduled quarterly game-day; a failed run blocks relying on
the standby.

### Inducing a failure (so Route 53 fails the primary health check)
We need the primary `/api/health` to start failing WITHOUT deleting anything.
Options, least-destructive first:

1. **Health-check target flip (safest, fully reversible):** temporarily point
   the Route 53 health check at a path the app returns non-200 for (e.g.
   `/api/health-FORCE-FAIL`). The primary app stays up and serving real users;
   only the *health check* fails, so Route 53 fails over to the standby. Revert
   the path to restore. **This is the recommended drill mechanism** — zero impact
   on the running primary, instantly reversible.
2. **Add a WAF block rule on `/api/health` (primary only):** block the health
   path at the edge so the checker gets 403. Reversible by deleting the rule.
3. **Pause the primary App Runner service:** `aws apprunner pause-service` —
   realistic (simulates a true regional/app outage) but takes minutes to
   pause/resume and briefly drops the primary for real users. Use for a
   full-fidelity drill, not routine checks.

An optional app-level switch makes drills cleanest: a `HEALTH_FORCE_FAIL=1` env
var that makes `/api/health` return 503 on the primary only. Flip it, watch
failover, flip it back. (Add in a later commit if we want repeatable drills.)

### Drill steps
1. Baseline: `./deploy/monitor.sh health` on the custom domain → 200 from EAST
   (confirm via the `config.region` in the health JSON).
2. Write a **sentinel**: log into the live app and create a throwaway note/entry
   (or a sentinel profile) so we can prove it survives the switch.
3. **Induce failure** (mechanism #1 above): flip the health-check target to a
   failing path.
4. Watch: `./deploy/monitor.sh watch` / repeatedly curl the domain. Within
   ~90–150s the health JSON `config.region` should flip to **us-west-2**.
   Confirm the `RegionFailoverBanner` shows during the gap.
5. **Verify data on the standby:** the sentinel from step 2 is present (proves
   Litestream replication + west restore). Measure wall-clock RTO.
6. **Write on the standby:** create a second sentinel while west is primary.
7. **Fail back:** revert the health-check target. Route 53 returns to EAST.
   Confirm the step-6 sentinel round-trips back to east (proves bidirectional
   CRR / Litestream and RPO ≤ 60s). *(Note: during active/passive, only one
   region writes at a time; fail-back reconciliation relies on the west WAL
   replicating back — document the direction of replication carefully.)*
8. Record: RTO, whether RPO ≤ 60s, that the standby decrypted DB+uploads+secret
   with west keys (no manual action), and that WAF did not block the checker.

### Pass criteria (gate)
- [ ] RTO ≤ 5 min to first successful standby response.
- [ ] Sentinel data present on the standby (no loss).
- [ ] Standby decrypts all state with us-west-2 keys, no manual key/IAM action.
- [ ] Failover banner displayed during the switch.
- [ ] Clean fail-back to east with no data divergence.

---

## Rollback / spin-down

Phase 2 is additive and reversible. To spin down the standby (the owner noted a
possible spin-down in 1–2 months):
1. Revert the Route 53 record from failover pair back to a simple record → east.
2. Delete the west App Runner service, WAF, custom domain, buckets, CRR config,
   secret replica, ECR replication rule, west IAM policies.
3. Optionally keep the MRK (harmless) or schedule the west replica for deletion.
The primary (phase 1) keeps running untouched throughout.

---

## Cost delta (rough, monthly)
Standby App Runner (warm min-1) ~$5–7, west WAF ~$9–11, 2 west S3 buckets +
CRR + replication requests ~$2–4, ECR replication storage ~$0.30, secret replica
~$0.80, west health check ~$0.50, KMS MRK replica ~$1. **~$18–25/mo on top of
phase 1**, i.e. ~$40–50/mo total — still inside the $50 budget alert (which we
may want to raise to ~$70 for headroom).
