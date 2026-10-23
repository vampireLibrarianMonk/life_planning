# Backlog — larger features (not yet started)

Captured 2026-10-23. These are feature-level items beyond the provisioning work
(see `01_user_provisioning.md`). Nothing here is built yet.

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

## 2. Developmental tracking for the child — ASQ-*style* (NOT yet; owner: "when we start")

**Decision locked (2026-10-23): original content, no ASQ reproduction.** We will
build an ASQ-*inspired* tracker using **our own abstracted developmental goals
and modified questionnaires** — NOT the verbatim Ages & Stages Questionnaires®
items, intervals, or cutoff scores. This sidesteps copyright entirely (ASQ is
published by Brookes Publishing, "all rights reserved"; verified at
agesandstages.com — it's a paid product behind purchase/subscription). The
parent can still complete the real ASQ **on paper with their pediatrician**
separately; our app just tracks our own goal structure + the child's progress.

### Why this is clean
- We reproduce **no proprietary expression** — our own wording and our own
  age-banded goal structure (mirroring the general *idea* of age-interval
  developmental domains, which is not itself protectable).
- Still a **screening/encouragement tracker, NOT a diagnosis** — UI copy must say
  "a prompt to talk to your pediatrician," no medical advice (house rule).

### Access model (owner decision) — differs from the journal
- **admin** (parents): full CRUD.
- **child** (owning child): can view (and participate as appropriate).
- **readonly** (extended family / grandparents): **CAN view** — developmental
  progress is something family follows along with.
- → use the **`require_profile_access`** guard (admin + readonly + the OWNING
  child; blocks cross-child), NOT the stricter `require_private_profile_access`.
- **Excluded from the public `/demo`** — "extended-family readonly" ≠ worldwide;
  the demo stays fake-data only.

### Likely shape when we build
- New per-profile domain: age-banded checkpoints across our developmental
  domains, parent-entered, status/score per item + optional notes, with a
  "discuss with your pediatrician" nudge (never pass/fail / never diagnostic).
- Separate **goals/questions** from **results** in the data model (clean even
  though both are our own content).
- Wire into the **archive export map + full-clean-delete cascade** (same as every
  other profile-scoped domain).
- Regression tests mirroring the role/profile-access guard tests.

**Action when we start:** (a) draft our own age-banded goal set + question
wording; (b) build the private data model (goals + results); (c) write the
no-medical-advice disclaimer copy.
