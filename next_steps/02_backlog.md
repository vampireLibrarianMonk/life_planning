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

## 2. ASQ-level developmental tracking for the child  (DO DUE DILIGENCE FIRST)

**Owner note:** "not yet — when we start." This is a *future* item; the point of
this entry is to record the **due-diligence findings and caveats** so we build it
responsibly when the time comes.

**What "ASQ" is:** the **Ages & Stages Questionnaires®** — a widely used parent-
completed developmental screening tool for children (roughly 1 month–6 years),
covering domains like communication, gross motor, fine motor, problem-solving,
and personal-social. There's also **ASQ:SE-2** for social-emotional screening.

### ⚠️ Due-diligence flags to resolve BEFORE building
1. **It is copyrighted / licensed, not free.** ASQ-3 and ASQ:SE-2 are published
   by Brookes Publishing. The questionnaires, scoring intervals, and cutoff
   values are **proprietary**. We almost certainly **cannot embed the actual ASQ
   questions, age intervals, or cutoff scores** without a license. → Confirm
   licensing terms before encoding any ASQ content. Safer default: let a parent
   **record their own results/observations** (scores they obtained elsewhere, or
   free-form developmental notes) rather than reproducing the instrument.
2. **It's a *screening* tool, not a diagnosis.** Must be framed as "a prompt to
   talk to your pediatrician," never as a medical assessment. The app gives no
   medical advice (house rule). UI copy must say so plainly.
3. **Sensitive health-adjacent data.** Developmental screening results are
   among the most private data about a child — treat them AT LEAST as private as
   the discernment journal (child+admin only, backend-enforced via the
   `require_private_profile_access` pattern we already have). Include in the
   archive/export + full-clean-delete paths.
4. **Age-interval model.** ASQ is organized by specific month intervals
   (2, 4, 6, 9, 12, … months). If we build our OWN developmental tracker instead
   of licensing ASQ, we can mirror the *structure* (age-banded checkpoints per
   domain) without copying ASQ's proprietary items — likely the cleanest path.

### Likely shape IF we proceed (pending #1)
- A new private, per-profile domain: age-interval checkpoints across
  developmental domains, parent-entered, with a status/score per item and a
  "discuss with pediatrician" nudge rather than a pass/fail.
- Backend: profile-scoped + `require_private_profile_access`; add to archive
  export map + delete cascade; author/privacy same as journals.
- Decision gate: **license real ASQ** vs **build an original age-banded
  screener** (no proprietary content). Recommend the latter unless a license is
  obtained.

**Action when we start:** (a) confirm ASQ licensing / choose original-vs-licensed;
(b) design the private data model; (c) write the medical-disclaimer copy.
