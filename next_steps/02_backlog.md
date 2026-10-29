# Backlog — larger features

Captured 2026-10-23, updated 2026-10-27. Feature-level items beyond the
provisioning work (see `01_user_provisioning.md`).

**Current state:**
- **#1 Manager's Dashboard** — specced, not built. No blockers; ready to start.
- **#2 Child Development (Early Growth Markers)** — ✅ **BUILT & LIVE (2026-10-27).**
  Dashboard section below Life Maps; age-group cards → objective CRUD + marks +
  accomplishment photos + private worries note + print stage sheet. Backend +
  frontend shipped; e2e verified green against the live deploy.
- **#3 Lineage bounty track** — reframed (2026-10-27): the Heritage pillar
  ALREADY covers lineage (family tree, ancestor research, migration map,
  artifacts), so NOT a new pillar — at most a small bounty-track enrichment of
  Heritage. Pending owner decision on whether it's worth adding.

---

## 1. Manager's Dashboard — CRUD user operations (admin)

**Goal:** an admin-only screen to manage *user accounts* (not profiles) from the
UI, instead of the local `provision_user.py` CLI / Swagger.

**Scope (CRUD on users):**
- **List** all users: username, display name, role, email, status (active /
  awaiting-setup / setup-link-expired), created date, last login if we track it.
- **Create** a user → same flow as the CLI: pick friendly type (father/mother→
  admin, visitor→readonly, child→child), enter name + email, send the 72h
  setup-link invitation via SES. Reuse `build_invitation` + the setup-token
  endpoint (no passwords ever set/emailed by an admin).
- **Resend invitation** → issue a fresh setup token + re-email (we already do
  this ad-hoc; make it a button). Needed because links expire in 72h.
- **Edit** → change display name / email / role. Changing role must re-check
  the access model (e.g. promoting readonly→admin, or linking a child to a
  profile via the existing `PATCH /profiles/{id}/user`).
- **Deactivate / delete** a user. Deactivate (disable login) is safer than hard
  delete; hard delete should block or reassign if the user owns a child profile.
- **Link/unlink a child** to their profile (surface the existing endpoint).

**Backend:** most endpoints exist (register, setup-token, profiles/{id}/user).
Likely need: `GET /api/users` (admin list), `PATCH /api/users/{id}` (role/
display/email), `DELETE`/deactivate, and a "resend-invite" convenience. All
**admin-only** (`require_admin`) with regression tests mirroring the existing
readonly/role guard tests. Consider an `active`/`disabled` flag on User +
login check.

**Frontend:** a `/users` (or dashboard tab) admin-only view; hidden for
readonly/child via the existing role gating. Reuse the role-chip + 403-toast
patterns.

**Safeguards:** never show password hashes; never let an admin set a password
directly (keep the setup-link model); confirm-destructive on delete/deactivate;
don't let an admin delete/demote the last remaining admin (lockout guard).

---

## 2. Child Development — early-childhood section (same level as Life Maps) — ✅ BUILT & LIVE (2026-10-27)

The on-screen section is titled **"Child Development"** (its own dashboard
section, directly below Life Maps). The underlying corpus of objectives is the
original, non-ASQ "Early Growth Markers" content — a formation on-ramp for ages
~2mo–5yr, NOT a clinical screen.

### Status (2026-10-26)
- ✅ **Copyright decision locked:** original content, NO ASQ reproduction. ASQ is
  a paid Brookes product (verified at agesandstages.com); we write our own items
  from public-domain facts (MedlinePlus/NIH, WHO, cross-checked AAP).
- ✅ **Corpus written + reviewed + delivered:**
  `draft_additions/developmental_checkpoints_draft.md` — 10 intervals (2,4,6,9,
  12,18,24,36,48,60 mo) × 5 domains × ~5 observable items, non-scoring tri-state
  **not yet / emerging / practicing**, pinned non-diagnostic banner, "what helps"
  tips, domain→pillar bridges, split free-text (family-shared "noticing &
  celebrating" vs. private "questions & worries"). Passed a multi-agent review
  (copyright, developmental accuracy, safety, format) + an app-competence /
  mission-fit / reviser panel (mission-fit verdict: FIT WITH GUARDRAILS).
  Emailed to Patrick + Sara for sign-off (committed `acd92c7`).
- ✅ **Alpha integration plan written:**
  `draft_additions/early_growth_markers_alpha_plan.md` (committed `c293436`).

### As-built (shipped 2026-10-27) — matches the plan below
- **Placement (owner-confirmed 2026-10-27):** its OWN dashboard section titled
  **"Child Development," at the same level as Life Maps and rendered directly
  below it** — NOT a pillar card, NOT inside the education pillar. Uses the Life
  Maps pattern (section `<h2>` + cards that open a dedicated view via a
  `__child_development__` sentinel).
- **Hierarchy:** Child Development → **age-group cards** → domains → **objectives**.
- **Storage = ZERO schema change:** objectives are `PillarEntry` rows tagged
  `category="child_development"` (family-readable) / `"child_development_private"`
  (worries, parent-only), with the domain persisted in the category suffix
  (e.g. `child_development:social_emotional`). `pillar` is set to an existing
  value only to satisfy the non-null column; the UI never surfaces them there.
  A new `Pillar` enum value is AVOIDED on purpose (SQLite VARCHAR+CHECK the
  additive boot migration can't widen); being a dashboard section like Life Maps,
  it doesn't need one.
- **Per-objective CRUD menu:** add/edit/mark/delete each objective (reuses
  `/entries` endpoints).
- **Accomplishment photos:** upload via the existing `EventAttachment`
  routes attached to the objective's `PillarEntry` (family-readable).
- **Tri-state → status:** not yet→not_started, emerging→in_progress,
  practicing→complete (introduced/practicing-status/mastered reserved/unused).
- **Age-group encoding:** label in `age_band` ("12mo"); numeric months in
  `age_years` as the sort key (UI must sort by `age_years`, not string age_band).
- **Privacy split (resolved + owner-confirmed):** objectives + photos +
  "celebrating" note on the existing `/entries` router (`require_profile_access`
  = admin + child + family readonly); "worries" on a NEW sub-route gated
  `require_private_profile_access` (admin + owning child only; readonly 403).
  Writes stay `require_admin_or_child`.
- **Configure:** seed-on-demand per age group via a server-side template route
  (mirrors `seed_data.py`), idempotent; "active" = presence-of-rows; deactivate
  = DELETE rows.
- **Print:** `@media print` + `window.print()` stage sheet (one age group/sheet,
  empty tri-state checkboxes, pinned banner); worries OMITTED from print in
  alpha. No server-side PDF.
- **Filtering:** normal pillar/education views AND `/demo` must exclude both
  `child_development*` categories.
- **Build order (loop):** (1) backend seed/CRUD + private worries route + photo
  upload + tests → (2) dashboard section + age-group view (12mo first, with the
  objective CRUD menu + photos) → (3) print sheet → (4) scale all age groups.

### Owner decisions (confirmed 2026-10-27)
1. ✅ **Placement:** same level as Life Maps, directly below it.
2. ✅ **Top-level cards = age groups;** drill in → domains → objectives.
3. ✅ **Visibility:** objectives + accomplishment photos family-readable;
   "worries" note parent/child-only (private route).

### Still open (finalize with slice 2; not blocking slice 1)
- **Corpus sign-off:** do Patrick + Sara approve the emailed corpus format/wording?
- **Who marks/edits objectives:** parents only, or the child too (child role can
  write)? Determines editable vs. read-only child view.
- **Print scope:** one age group per sheet (planned) vs. an "all active groups"
  booklet.
- **Worries on print:** omit in alpha (planned) vs. a separate parent-only print.

**Action to start:** alpha slice 1 (backend seed/CRUD + private worries route +
photo upload + tests). Wire into the archive export map + full-clean-delete
cascade at that point.

### ⚠️ Follow-up for Child Development (archive/delete coverage)
Child Development rows are `PillarEntry` rows, so the existing archive export +
full-clean-delete already sweep them up **generically** (they're exported in
`pillars/entries.json` and deleted with the profile's entries). BUT confirm the
private `child_development_private` worries note and objective photos also travel
correctly on restore, and that normal pillar export doesn't double-handle them.
Add a round-trip assertion when touching archive next. (Not urgent — nothing is
lost today; it's a correctness check.)

---

## 3. Lineage bounty track — ENRICH the existing Heritage pillar (not a new pillar)

**Owner caught (2026-10-27): this would largely repeat the Heritage pillar.**
Heritage & Language ALREADY covers lineage:
- Its about-text literally says it "combines identity investigation ('Who do you
  think you are?') with … family origins, stories, artifacts, and traditions."
- Seeded milestones already include: "Family tree constructed", "Migration map
  started", "Artifacts preserved/digitized" (6-12); "Ancestor research — one
  person per year", "Faith heritage explored", "Occupation patterns identified",
  "Health/genetic awareness" (13-18); plus "Learns basic family tree" and
  "Lessons purchased by ancestors documented" elsewhere.

**So: do NOT build a new pillar.** The genuinely-new part of the owner's idea is
turning lineage research into **rewarded, evidence-backed BOUNTIES** (the current
items are checkbox milestones, not bounty tasks with tiers/rewards/evidence).

### Proposed (small, additive): a Heritage "lineage" bounty set
- Add seeded **bounties** under the existing `heritage` pillar (reuse the Bounty
  model + tier/decay mechanics already in the app — no new pillar, no schema
  change). Examples:
  - Interview a living relative; record one sourced story/fact per generation.
  - Extend the tree back one more generation **with a primary source** (tiered:
    deeper + better-sourced = higher tier).
  - Find a primary record (certificate, census, ship manifest, headstone photo).
  - Map an ancestor's migration and place them in a historical moment.
- **Evidence:** reuse `EventAttachment` for scans/photos (already supported).
- **Reward depth AND source quality** so it can't be farmed with unverifiable
  claims — mirror the existing bounty criteria/decay pattern.

### Guardrails / notes
- **IP:** the "Who do you think you are?" phrase is ALREADY in the heritage
  about-text as a lowercase thematic nod, not as branding — keep it that way;
  do not name a feature after the show or reproduce its format.
- **Privacy:** heritage is family-readable (admin + child + extended-family
  readonly) — appropriate for lineage. Flag: living relatives' PII entered in
  notes is the one sensitivity.
- **Decision for owner:** (a) is enriching Heritage with a lineage bounty set
  worth doing, or are the existing milestones enough? (b) how many bounties /
  what tiers?

**Status: reframed — likely a small seed-data addition to Heritage, pending the
owner decision above. Not a standalone pillar.**

---

## 4. Automated cross-region failover/fail-back with staged alerting — DESIGN (not built)

> **Origin:** owner asked whether west can be shut down and auto-booted only on
> an east outage, with the user alerted at every lifecycle stage. Explored
> interactively 2026-10-29 and pressure-tested with a 2-agent panel
> (adversarial + advocate/researcher). This entry is the **design + decision
> record**, not an approved build.

### Goal (as the owner specified it)
On an **east outage**: alert user → boot west → alert "west booting" → alert
"west up" → keep monitoring east → on **east recovery**: alert → transition back
to east → alert "shifting back" → alert "east up" → shut west down → alert "west
down". A fully narrated, auto-driven failover **and** fail-back loop.

### What DR pattern this is
Textbook **Pilot Light** (AWS Well-Architected REL13-BP02): data-replication
resources always on (S3 + Litestream + CRR), app compute **off** (west App
Runner paused) until a disaster "lights the pilot." This is a deliberate
*downgrade* from the current **Warm Standby** (west running 24/7) — trading a
slower RTO for ~$5-7/mo of west compute.

### Chosen architecture (after narrowing options with the owner)
- **Mutual cross-region monitors:** Orchestrator-West (Lambda in us-west-2)
  watches/rescues east; Orchestrator-East (Lambda in us-east-1) watches/rescues
  west. Each lives OUTSIDE the region it rescues (so the watcher survives its
  target's death). Global Route 53 health checks remain the user-facing routing
  signal.
- **Compute:** EventBridge Scheduler → Lambda (~30-60s poll) as a code-driven
  state machine. **Rejected:** Step Functions Standard (~$25-50/mo of state-
  transition cost for a 24/7 loop — would ~double the app's bill); Route 53 ARC
  (~$1,800/mo — correct but absurd at this scale).
- **Split-brain arbiter:** a leased `current_primary` record + monotonic
  **fencing token** (loser-refuses-to-write), doubling as the lifecycle phase
  tracker.
- **West off/on:** App Runner pause/resume. **Fail-back:** gated by a west→east
  reconciliation copy (CRR is east→west only).

### ⚠️ Panel findings — the design as first sketched is NOT safe; corrections required
Both agents independently flagged the same load-bearing problems:
1. **DynamoDB *Global Table* is the WRONG arbiter.** Cross-region replication is
   eventually-consistent / last-writer-wins, so during the exact partition you
   need it, **both** regions' conditional writes can succeed locally → the
   arbiter itself splits brain. **Fix:** a SINGLE authoritative lease table in a
   **neutral third region** (e.g. us-east-2); both orchestrators do conditional
   writes against that one table (real single-region strong consistency), so the
   arbiter survives either primary/standby region failing.
2. **Fencing must be ENFORCED AT THE WRITER, not just held.** SQLite/Litestream/
   S3 don't enforce a token. Litestream's own docs warn: two writers into the
   same bucket/path **can corrupt the replica beyond restore**. **Fix:** write a
   generation sentinel to the S3 path on promotion; the Litestream writer
   refuses to run unless it holds the current generation; use per-generation S3
   prefixes (`/db/gen=k/`) so a stale writer can only orphan its own prefix.
3. **Auto fail-back is the real data-loss trap.** CRR is east→west ONLY — west's
   outage-window writes have NO path back to east. Automatic fail-back on a 60s
   TTL **discards them faster than a human could intervene** — i.e. the
   automation *guarantees* the loss it's meant to prevent. **Fix:** fail-back is
   a deliberate, manual-gated step: quiesce west writes → copy west replica →
   east BEFORE east resumes → then re-point. Never fully automate this direction.
4. **Scale-to-zero introduces a HARD-DOWN window that doesn't exist today.** A
   paused west fails its health check, so Route 53 has no healthy secondary
   during the ~3-6 min cold boot (App Runner resume + `litestream restore`). The
   current warm standby has ~1-2 min RTO with no hard-down gap.
5. **RTO gets WORSE, not better:** automated pilot-light path ~3-6 min
   (poll + async resume + cold restore + TTL) vs. ~1-2 min warm today.
6. **Net saving is only ~$4-6/mo** after the new Lambda/DynamoDB/SNS/cross-region
   costs — in exchange for ~5 new moving parts that must themselves be correct,
   tested (in failure modes that are hard to test), and maintained.

### ✅ App Runner platform status — VERIFIED 2026-10-29 (official AWS source)
Confirmed against the official AWS App Runner product page
(https://aws.amazon.com/apprunner/), verbatim:

> "**End of support notice** — AWS App Runner will no longer accept new
> customers starting on **April 30, 2026**. Your existing App Runner services
> will remain operational and accessible. AWS continues to invest in security
> and availability, but we do not plan to introduce new features."

Implications for this app:
- **Our existing east + west services keep running** — not evicted. No immediate
  action forced.
- **No new features / maintenance-mode** — the platform is being wound down;
  closed to new customers is the classic first step toward eventual EOL (no EOL
  date published yet).
- **Strategic read:** do NOT invest in bespoke App Runner-specific automation
  (pause/resume orchestration). This materially strengthens the "DON'T BUILD
  (option a)" verdict for this item, and suggests a separate future backlog
  item: **plan a migration off App Runner to AWS's named successor,
  Amazon ECS Express Mode** — the App Runner page explicitly states: "For
  deploying and running containerized applications, we recommend Amazon ECS
  Express Mode, a new capability in Amazon ECS" and links official migration
  guidance (verified 2026-10-29). ECS Express Mode is a like-for-like
  successor (give it a container; it manages LB/scaling/networking), so the
  migration should be relatively direct. Not urgent (existing services keep
  running), but track it before any hard EOL.

### Panel verdicts (they split — recorded honestly)
- **Adversarial agent: ABANDON.** "Cure worse than the disease" for a $33/mo
  app: removes the warm secondary, speeds up the data-destroying fail-back,
  relies on a non-enforcing fence + a splittable lease, all to save a few
  dollars on a possibly-retiring platform. Current warm standby already meets
  the owner's stated risk posture.
- **Advocate agent: BUILD-SIMPLIFIED.** Pilot light is the right altitude and
  RTO/RPO easily satisfy the owner; but build only the safe subset and fix the
  arbiter first.

### Recommended path IF pursued (phased; safe subset only)
- **Phase 0 — Prove the MANUAL runbook first** (pause/resume, restore, R53 flip,
  west→east reconciliation copy). Time a real manual failover + fail-back. (This
  largely exists already as `deploy/failover_control.sh` — extend it.)
- **Phase 1 — Lease + writer-enforced fencing, no automation.** Authoritative
  lease table in a neutral 3rd region; generation numbers; per-generation S3
  prefixes; prove split-brain is impossible by trying to force two writers.
- **Phase 2 — Detection + staged SNS alerts, human-in-the-loop** (actions
  proposed, executed by a click). Add flap hysteresis (N≥3 fail / M≥5 ok +
  cooldown).
- **Phase 3 — Automate ONLY the east→west "up" direction** (the safe one).
- **Phase 4 — Fail-back stays MANUAL / explicitly gated** (the dangerous one);
  automate last, if ever, and only after the reconciliation copy is proven.

### Owner decision needed
Given it nets ~$4-6/mo, **worsens** RTO, adds a hard-down window + real
corruption surface, and the current warm standby already meets the stated risk
posture (~5s RPO east→west OK, dual-region failure out of scope):
- **(a) DON'T BUILD** — keep warm standby at ~$33/mo (simplest, safest, matches
  posture). *Default recommendation.*
- **(b) BUILD-SIMPLIFIED as an EDUCATIONAL exercise** — Phases 0-2 + Phase 3
  only, fail-back manual, arbiter in a 3rd region. Accept the cost/RTO tradeoffs
  as tuition, not savings.
- **(c) Go the OTHER way** — if $/simplicity matter most, consider single-region
  + Litestream backups + S3 versioning (drop the standby entirely), which also
  matches the risk tolerance and saves more than this automation would.

### App Runner → ECS Express Mode migration: ARM feasibility + cost (researched 2026-10-29)

**ARM/Graviton feasibility — YES, with a one-line fix.** Verified against the
actual image: `node:22-alpine` + `python:3.12-slim` both publish arm64; every
compiled Python dep (pydantic-core, cryptography, bcrypt, uvloop/httptools)
ships aarch64 wheels. **Only blocker:** the Dockerfile hardcodes the Litestream
`linux-amd64` binary — change to `linux-arm64` and build `--platform=linux/arm64`.
ARM Fargate is ~20% cheaper than x86 (API-verified: $0.03238 vs $0.04048 per
vCPU-hr; $0.00356 vs $0.004445 per GB-hr). Take ARM in any migration.

**ALB question — RESOLVED from the AWS ECS FAQ (verified 2026-10-29):** "By
default, Express Mode creates services using AWS Fargate and **includes an
Application Load Balancer (ALB)**... with a default URL provided by AWS." And:
"no additional charge for Express Mode; you pay for the resources created — AWS
Fargate, **Application Load Balancer**, and CloudWatch." So Express Mode's
default = Fargate + a per-service ALB you pay for.

**Rates (all AWS Pricing API-verified, us-east-1 = us-west-2):** Fargate x86
$0.04048/vCPU-hr + $0.004445/GB-hr; ARM 20% less; ALB $0.0225/hr (~$16.43/mo) +
$0.008/LCU-hr; public IPv4 $0.005/hr (~$3.65/mo). Your task = 0.25 vCPU/0.5 GB.

**Cost scenarios (TOTAL monthly app bill; ~$28 non-compute infra stays):**

| Scenario | Compute | Ingress | **Total** | vs $33 |
|---|---|---|---|---|
| Current App Runner (both regions) | $4.75 | bundled | **~$33** | — |
| Express default, x86 + ALB (2 regions) | $18.02 | $32.85 | **~$79** | +$46 |
| Express default, ARM + ALB (2 regions) | $14.42 | $32.85 | **~$76** | +$43 |
| **No-ALB: Fargate public-IP, ARM (2 regions)** | $14.42 | $7.30 | **~$50** | +$17 |
| No-ALB: Fargate public-IP, x86 (2 regions) | $18.02 | $7.30 | ~$54 | +$21 |
| Single-region Express (ARM + 1 ALB) | $7.21 | $16.43 | **~$40** | +$7 |
| **Single-region, no-ALB public-IP, ARM** | $7.21 | $3.65 | **~$27** | **−$6** |

**The no-ALB option (owner asked to consider):** a Fargate task can run with
`assignPublicIp=ENABLED` and be reached directly — **no load balancer at all**,
paying only the ~$3.65/mo public-IPv4 charge instead of ~$16.43/mo per ALB. This
is the single biggest lever (ALB is the dominant new cost, more than the compute
itself). Tradeoffs/caveats of the no-ALB path:
- You lose the ALB's managed TLS + the auto-provisioned default URL. You'd
  terminate TLS at the app (or front it with **CloudFront**, which bills per-
  request + data and can be cheaper than an ALB at this traffic) and point
  Route 53 at the task's public IP (which changes on redeploy — needs a small
  updater, or use CloudFront/a stable endpoint in front).
- It's NOT the Express Mode "default" — Express Mode wants to give you an ALB. A
  no-ALB build is really "plain ECS/Fargate task," i.e. you'd skip Express Mode's
  convenience to save the ALB. So "Express Mode" and "no ALB" are somewhat at
  odds; the no-ALB number is the plain-Fargate figure.
- The IP-per-task churn + manual TLS is real operational work — weigh it against
  the ~$9/mo (dual) or ~$13/mo (vs ALB, single) saving.

**Takeaways:**
1. A 1:1 dual-region lift to Express-Mode-default is the WORST case (~$76-79/mo,
   over the $70 cap) — a second ALB on a standby serving ~no traffic is wasteful.
2. The ALB-per-service model argues strongly for **single-region** on migration:
   single-region Express+ALB ≈ **$40/mo**; single-region no-ALB public-IP ARM ≈
   **$27/mo** (actually CHEAPER than today, but with the TLS/IP caveats above).
3. No urgency — App Runner runs indefinitely. When migrating: go **ARM**, and
   decide ALB-vs-no-ALB and dual-vs-single-region together (they interact).

**Status: DESIGN ONLY — not built. Blocked on the owner decision (a)/(b)/(c).
App Runner platform-status claim VERIFIED (2026-10-29): closed to new customers
2026-04-30, existing services keep running, maintenance-mode only — this
strengthens option (a) DON'T BUILD and adds a separate "migrate off App Runner"
item to consider.**
