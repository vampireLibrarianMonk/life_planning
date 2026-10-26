# Backlog — larger features

Captured 2026-10-23, updated 2026-10-26. Feature-level items beyond the
provisioning work (see `01_user_provisioning.md`).

**Current state:**
- **#1 Manager's Dashboard** — specced, not built. No blockers; ready to start.
- **#2 Early Growth Markers** — corpus + alpha plan written, reviewed, and
  emailed to Patrick + Sara. **BLOCKED on 5 owner answers** (see that section)
  before any code is written.

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

## 2. Early Growth Markers — early-childhood developmental tracker (ALPHA planned)

Renamed from "ASQ-style tracker." Original, non-ASQ content; a formation on-ramp
for ages ~2mo–5yr, NOT a clinical screen.

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

### Alpha build plan (from the companion doc) — NOT yet built
- **Storage = ZERO schema change:** markers are `PillarEntry` rows under the
  existing `education` pillar + `category="devcheck"` (milestones, family-
  readable) and `category="devcheck_private"` (worries, parent-only). A new
  `Pillar` enum value is AVOIDED on purpose — SQLite stores the enum as a
  VARCHAR+CHECK that the additive boot migration can't widen.
- **Tri-state → status:** not yet→not_started, emerging→in_progress,
  practicing→complete (introduced/practicing-status/mastered reserved/unused).
- **Interval encoding:** label in `age_band` ("12mo"); numeric months in
  `age_years` as the sort key (UI must sort by `age_years`, not string age_band).
- **Privacy split (resolved):** milestones + "celebrating" note on the existing
  `/entries` router (`require_profile_access` = admin + child + family readonly);
  "worries" on a NEW sub-route gated `require_private_profile_access` (admin +
  owning child only; readonly 403). Writes stay `require_admin_or_child`.
- **Configure:** seed-on-demand per interval via a server-side template route
  (mirrors `seed_data.py`), idempotent; "active" = presence-of-rows; deactivate
  = DELETE rows. On a Profile-page "Early Growth Markers" section.
- **Print:** `@media print` + `window.print()` stage sheet (one interval/sheet,
  empty tri-state checkboxes, pinned banner); worries OMITTED from print in
  alpha. No server-side PDF.
- **Filtering:** normal education views AND `/demo` must exclude both `devcheck`
  categories.
- **Build order (loop):** (1) backend seed/CRUD + private worries route + tests
  → (2) configure UI (12mo first) → (3) print sheet → (4) scale all intervals.

### ⛔ BLOCKED ON OWNER ANSWERS — need Patrick + Sara before building
1. **Corpus sign-off:** do you + Sara approve the corpus format/wording as
   emailed? (Gate for everything below.)
2. **Domain encoding:** persist domain as a tag (e.g. `category="devcheck:social_emotional"`)
   for clean grouping, or keep domain as a UI-only heading? (Recommend: persist.)
3. **Who marks items:** parents only, or the child too (child role can write)?
   Determines whether the child's sheet is editable or read-only.
4. **Print scope:** one interval per sheet (recommended) or an "all active
   intervals" booklet?
5. **Worries on print:** omit in alpha (current plan), or provide a separate
   parent-only print that includes them?

**Action when unblocked:** start alpha slice 1 (backend seed/CRUD + private
worries route + tests). Wire into the archive export map + full-clean-delete
cascade at that point.
