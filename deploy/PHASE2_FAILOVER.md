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

### Topology & failover sequence

![Dual-region deployment](../diagrams/architecture_deployment.png)

![Failover & fail-back sequence](../diagrams/architecture_failover.png)

### Fail-back — DATA-LOSS HAZARD + gated runbook (added 2026-10-27)

> **⚠️ The automatic fail-back is NOT data-safe.** The Route 53 record is a
> PRIMARY/SECONDARY pair with health checks on both sides, so east auto-reclaims
> traffic the instant its health check recovers. But CRR is **one-directional
> (east→west only)** — the west DB bucket has **no** replication back to east.
> So a *real* east outage with writes landing on west, followed by auto-fail-back,
> **silently loses every write made on west**: east boots and `litestream restore`
> pulls from its own frozen east bucket. The 2026-10-21 drill's "no data
> divergence" claim is **UNVERIFIED for a real outage** — that drill used the
> health-check-flip mechanism where east keeps running and writing, so east's
> bucket never went stale and the bug could not surface.
>
> **Why we do NOT "just make CRR bidirectional":** two Litestream writers
> replicating into each other's bucket interleaves independent generation chains
> on the same `life_plan.db/` prefix → SQLite/WAL corruption (the active/active
> hazard single-writer exists to prevent).
>
> **The correct procedure is a GATED fail-back.** Use
> `deploy/failover_control.sh` (safe primitives; mutating actions require a typed
> confirmation):
>
> 1. During a real east outage, once west is serving, run `hold-east` so east
>    will **not** auto-reclaim traffic when it recovers (detach the primary
>    health check per the printed manual step — DNS edits are left manual on
>    purpose).
> 2. When east is healthy again but still held, run `reconcile-to-east` — it
>    `aws s3 sync`s west's **entire** Litestream generation tree
>    (`life_plan.db/`) into the east bucket so east will restore west's data,
>    not its stale copy.
> 3. Redeploy/restart east, verify it serves the reconciled data (sentinel), then
>    `release-east` to re-attach the primary health check and resume normal
>    east-primary failover.
>
> If **no writes** happened on west during the outage, steps 1–2 are unnecessary
> and auto-fail-back is harmless. The hazard is specifically write-on-standby +
> auto-fail-back.
>
> **OWNER DECISION STILL OPEN:** whether to make fail-back *permanently* manual
> (drop the SECONDARY→PRIMARY auto-promotion by detaching the primary health
> check by default). That is a live Route 53 change with its own failure modes
> and is left for an explicit owner go-ahead; the runbook above makes the current
> auto-config safe to operate in the meantime.

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

> **Progress:** ALL STEPS DONE & verified (2026-10-21). MRK in both regions;
> data re-encrypted; west S3 + CRR (backfilled); secrets replicated to west;
> ECR registry replication; west App Runner standby RUNNING + MaxSize=1 + custom
> domain (own ACM cert); Route 53 **failover pair** live (PRIMARY east /
> SECONDARY west, each with its own health check). **Failover drill PASSED** —
> see the game-day section. Phase 2 is complete and operational.

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

> **DRILL RESULT (2026-10-21): PASS.** Full cycle verified — east (primary) →
> east health check forced unhealthy → **auto-failover to west** (domain served
> `region: us-west-2`, standby had the real data) → east health check restored →
> **auto-fail-back to east**. RTO ~90–120s each direction (detection + 60s TTL),
> matching target. Live users unaffected (the east app kept running; only the
> health-check *path* was flipped).
>
> **Important lesson — the SPA catch-all returns HTTP 200 for ANY unknown path**
> (unknown `/api/*` included; it serves index.html). So a "point the health
> check at a fake path" drill does NOT fail. Use a path that genuinely returns
> non-2xx: `/api/profiles/` returns **401** unauthenticated and is the reliable
> drill trigger. (Cleaner future option: add a `HEALTH_FORCE_FAIL=1` env toggle
> that makes `/api/health` return 503 on demand.)

> **DRILL RESULT (2026-10-27): PASS (cookie-auth era).** Re-ran the health-check
> flip after the httpOnly-cookie auth migration. Failover east→west in ~2 min;
> **west served the new bundle (`index-CRjCGAlj.js`) and the cookie flow worked
> end-to-end for all three users** (admin, admin-readonly, robflan): login set
> `lp_auth` (HttpOnly/SameSite=strict/Secure), `/api/auth/me` + `/api/profiles/`
> authorized by cookie alone. Clean fail-back to east in ~95s.
>
> **⚠️ OPERATIONAL FINDING — west was running STALE code before this drill.**
> Although both services have `AutoDeploymentsEnabled=true` on `:latest`, App
> Runner's auto-deploy fires on a **direct push** to the watched repo, **not**
> on a **cross-region-replicated** image landing. So after each
> `build_push.sh`, east auto-deploys but **west keeps running its old image**
> (the new digest WAS present in west ECR — same sha — but the service hadn't
> rolled it). The standby had been stale since 2026-10-21 until a manual
> `aws apprunner start-deployment --service-arn "$SERVICE_ARN_WEST"` this drill.
> **FIX APPLIED (2026-10-27):** `deploy/build_push.sh` now triggers an explicit
> `aws apprunner start-deployment` for the WEST service after the push (gated on
> `$SERVICE_ARN_WEST`, best-effort so replication lag can't fail the primary
> deploy). Both regions now roll the same image on every deploy. If west ever
> no-ops due to replication lag, just re-run the printed `start-deployment`.

We need the primary `/api/health` to start failing WITHOUT deleting anything.
Options, least-destructive first:

1. **Health-check target flip (safest, fully reversible, USED):** temporarily
   point the primary's Route 53 health check at a path that returns non-2xx —
   use `/api/profiles/` (401), NOT a made-up path (which returns 200 via the SPA
   fallback). The primary app keeps serving real users; only the *health check*
   fails, so Route 53 fails over to west. Revert to `/api/health` to fail back.
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

## TWO distinct things to test (infra failover vs. user-facing UX)

A key insight from the 2026-10-21 drill: **the health-check-flip drill proves
the INFRASTRUCTURE fails over, but NOT the user-facing banner.** They are
separate tests with different mechanisms.

| Test | Mechanism | What it proves | User impact |
|------|-----------|----------------|-------------|
| **A. Infra failover** | Flip the primary's Route 53 health-check path to a non-2xx path (`/api/profiles/`). The east app KEEPS RUNNING. | DNS reroutes east→west, standby serves real data, auto fail-back. | **None** — safe, routine, reversible. |
| **B. User-facing UX (the banner)** | A **real** east outage so a loaded browser's requests actually fail: `aws apprunner pause-service` on east, or a temporary WAF block-all on east, or a `HEALTH_FORCE_FAIL` app toggle. | The `RegionFailoverBanner` fires (shows "switching region") during the ~90s gap, then the session recovers on west. | **Real brief outage** — full-fidelity, not routine. |

**Why test A does not show the banner:** `RegionFailoverBanner` only appears
after ~3 consecutive failed `/api/health` calls from the *browser*. In test A
the east app never stops serving, so the user's requests keep succeeding (on
east) until DNS moves them to west — a seamless switch with **no failed
requests, so the banner never triggers**. The banner is correctly designed for a
*genuine* outage, which test A does not create.

**To actually see the transition message**, run test B — recommended mechanism
is the app toggle below (cleanest + repeatable); `pause-service` is the most
realistic but slower to pause/resume.

### Proposed `HEALTH_FORCE_FAIL` toggle (clean repeatable UX drill)

> **BUILT & VERIFIED 2026-10-21.** The toggle exists and a real user-facing
> failover was run end-to-end. Browser-simulation result: east
> `HEALTH_FORCE_FAIL=1` → `/api/health` 503 → **banner "Switching to the backup
> region" appeared after ~3s (2 consecutive failed polls) and stayed up ~97s**
> until Route 53 re-pointed the domain to us-west-2, then auto-dismissed.
> Confirms the banner reliably covers the full ~90s DNS-failover gap.

**Critical design requirement discovered:** App Runner gates its *deployment* on
the service health-check path. If that path is `/api/health`, enabling
`HEALTH_FORCE_FAIL` makes the deploy hang and roll back (App Runner never sees a
healthy new version). **Fix:** two separate endpoints —
- **`/api/alive`** — always 200; this is App Runner's **service health-check
  path** (set via `update-service --health-check-configuration Path=/api/alive`).
  Unaffected by the drill, so deploys/toggles never roll back.
- **`/api/health`** — reports mode/region AND honors `HEALTH_FORCE_FAIL` (503);
  this is what **Route 53 failover** and the **browser banner** watch.

Note: the WAF only allow-lists `/api/health`; `/api/alive` is reachable by App
Runner's internal checker (not via the WAF/edge), which is sufficient.

How the toggle makes `/api/health` fail: env var read at request time, returns
503 when `HEALTH_FORCE_FAIL=1`, so BOTH Route 53 and the browser poll fail →
real user-visible failover. Set back to `0`/unset to recover.

### Drill: trigger a real user-facing failover (repeatable)
```bash
set -a; . ./.arn-env; set +a
# 1. Enable on EAST only (redeploys; succeeds because App Runner watches /api/alive):
aws apprunner update-service --service-arn "$SERVICE_ARN" --region us-east-1 \
  --cli-input-json file://<east-service-json-with HEALTH_FORCE_FAIL=1>
# 2. Load the site in a browser — within ~3s the "Switching to the backup
#    region" banner appears; ~90s later the session is served by us-west-2.
# 3. Recover: re-run update-service WITHOUT HEALTH_FORCE_FAIL. Domain returns to east.
```
(The CLI builds the full env block; see the session history / monitor.sh.)

### Full-fidelity drill via pause (no code change)
```bash
aws apprunner pause-service  --service-arn <EAST_SERVICE_ARN> --region us-east-1
# ... load the site in a browser: requests fail, banner appears, ~90s later
#     the session is served by west. Verify data present.
aws apprunner resume-service --service-arn <EAST_SERVICE_ARN> --region us-east-1
```

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
