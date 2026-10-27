# Backlog — larger features

Captured 2026-10-23, updated 2026-10-27. Feature-level items beyond the
provisioning work (see `01_user_provisioning.md`).

**Current state:**
- **#1 Manager's Dashboard** — specced, not built. No blockers; ready to start.
- **#2 Child Development (Early Growth Markers)** — ✅ **BUILT & LIVE (2026-10-27).**
  Dashboard section below Life Maps; age-group cards → objective CRUD + marks +
  accomplishment photos + private worries note + print stage sheet. Backend +
  frontend shipped; e2e verified green against the live deploy.
- **#3 Lineage / "Who Do You Think You Are"-style pillar** — NEW, specced below;
  not built.

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

## 3. Lineage pillar — trace the child's family tree (inspired by genealogy TV)

**Idea (owner, 2026-10-27):** a pillar themed on the *genealogy-journey* concept
popularized by the show "Who Do You Think You Are?" — give the child **bounties
to trace their lineage as far back as they can go**, in an abstract/structured
way that rewards real research and family interviews.

### ⚠️ IP / naming guardrail (same lesson as ASQ)
"Who Do You Think You Are?" is a **copyrighted TV format + trademark** (BBC/
licensed productions). We take the *idea* (researching one's ancestry) — which
is not protectable — but must **NOT** name the pillar after the show, reproduce
its episode structure/scripts/branding, or imply affiliation. Use our own name
(candidates: **"Roots & Lineage," "Where You Come From," "Ancestry Quest," or
fold into the existing `heritage` pillar**). Write all content originally.

### Likely shape (to be designed with the agent panel before building)
- **Home:** most naturally an extension of the existing **`heritage`** pillar
  (Heritage & Language already covers family origins, stories, artifacts) — OR a
  sibling section. Decide: new concept inside `heritage` vs. its own surface.
- **Bounties (abstract, research-driven), e.g.:**
  - Interview a living relative and record one story / fact per generation.
  - Build the tree back N generations (name, birth/place, a source).
  - Find a primary source (certificate, record, photo, headstone, ship manifest).
  - Map a migration/route; place an ancestor in a historical moment.
  - Tiered rewards that scale with how far back / how well-sourced (mirrors the
    existing bounty tier + decay mechanics).
- **Evidence:** reuse `EventAttachment` for scans/photos of records and artifacts.
- **Privacy:** lineage is a family/heritage good — likely **family-readable**
  (admin + child + extended-family readonly, like heritage), NOT parent-private.
  Living relatives' PII in notes is the one sensitivity to flag in the design.
- **Storage:** reuse `PillarEntry` + `Bounty` patterns; prefer **no new Pillar
  enum value** (reuse `heritage` or a dashboard-section like Child Development)
  to avoid the SQLite enum-CHECK migration wall.

### Open questions for design
1. New pillar/section name (NOT the show's name) — owner pick.
2. Live inside `heritage` vs. its own top-level section?
3. Bounty set + tiering: what counts as "as far back as they can go," and how do
   we reward depth vs. source quality without it becoming unverifiable?
4. How to handle **living relatives' PII** entered during research.

**Process when we start:** run the same panel (app-competence + mission-fit +
reviser) + copyright pass on any content, exactly like Child Development.
