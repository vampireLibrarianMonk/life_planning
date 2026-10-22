# Next Step: User Provisioning & Role Separation

> ## ✅ Readonly CRUD-hiding DONE (2026-10-21)
> Every live CRUD control is now hidden for `readonly` (inline `canWrite =
> !isReadonly()` gate in Profile.jsx + Economy.jsx). Status toggles (milestone
> 6-state, bounty/wishlist status) render as STATIC badges for readonly so state
> stays visible. Added: a role/identity chip in the Dashboard header for all
> roles, and a global 403 interceptor (`api.js` → `ForbiddenToast`) as a
> defense-in-depth "that change wasn't saved" toast. Backend is the real
> boundary; a regression test (`tests/test_readonly_enforcement.py`) asserts
> every write route depends on a readonly-blocking guard so future leaks fail CI.
>
> ### Completed since the adversarial review:
> - ✅ **Lock down child writes** (Task 3): behavior-incident create/delete/update
>   and bounty Complete→Paid are now admin-only (a child can't score their own
>   behavior or pay themselves). Backend-enforced + UI-hidden + regression tests.
> - ✅ **Sensitive-read privacy**: the behavior-incident log, private discernment
>   journals, and aggregate financial totals (earnings summary, fund balances/
>   ledgers) are private to the child + admin via `require_private_access`;
>   `/eligibility` returns tier-only for readonly. Individual bounty/wishlist
>   dollar amounts stay visible to readonly. Verified live against the
>   `admin-readonly` account.
>
> ### Remaining TODO (ordered; worldwide access is LAST):
> 1. **Per-profile read scoping** (adversarial review Task 4): readonly/child
>    currently read ALL profiles. Owner accepted "all profiles" for the single-
>    family case; revisit the `authorize_profile_access` + ProfileAccess grant
>    path before adding any non-family users.
> 2. _(LAST)_ **Worldwide / anonymized public readonly profile**: build a default
>    "demo" profile that unattributed, worldwide readonly users can view without
>    exposing a real child's name/DOB/photos/private data. Decide at that point
>    whether to also tighten photo access (currently open to close-family
>    readonly, which the owner confirmed is fine for now). **Do this last.**

---

Strategy for adding proper user provisioning (username≠email, three real user
types, secure credential delivery) to the Life Plan Tracker. Decided via an
adversarial design review (Pragmatic Builder vs. Safety Critic → Finalizer).

**Owner decisions locked in:**
- **Delivery mechanism: Option 1** — full one-time **setup link emailed** to the
  user (no password ever emailed or stored in plaintext).
- **Test case:** the father/admin account — username `<admin-username>`,
  email `<owner-email>`, type `father`.

Status: **BUILT, DEPLOYED, and in use** (2026-10-21). See "OUTCOME & lessons
learned" below. The first admin account (`pmflani` / Patrick Flanigan) was
provisioned live and the setup-link email delivered via SES.

---

## Why (the problems this solves)

1. **Separate username from email.** Today `users` has `username` (login id),
   `display_name`, `role`, `hashed_password` — but **no email**. Login stays
   username-based; email becomes contact/delivery metadata only.
2. **Three user types map to the EXISTING 3 roles** (no new role needed):
   | Friendly type | Real role | Person |
   |---------------|-----------|--------|
   | father / mother | `admin` | parent — full CRUD |
   | child | `child` (default issued as `readonly`) | the profile subject, e.g. Robert |
   | visitor | `readonly` | a relative — view only |
3. **Never email a reusable password.** The agreed-and-overruling safety call:
   emailing a plaintext password (which lives forever in an inbox) is rejected,
   especially for an app holding a minor's records. Instead: email a **one-time,
   24-hour, single-use setup link**; the user sets their own password; the app
   only ever stores the bcrypt hash.
4. **No per-user Secrets Manager entries.** Secrets Manager keeps doing ONLY its
   current job (the single admin-bootstrap secret + the JWT secret). The bcrypt
   hash in the DB is the only stored form of any real password.

---

## Verified current state (as of 2026-10-20)

- `models.py`: `User` = username(unique)/display_name/hashed_password/role/
  created_at. **No email column.** `Role` enum = `admin|child|readonly`.
  `Profile.user_id` is a nullable FK (child-user linkage already possible).
- `auth.py`: login is **username-only**. `require_admin_or_child` grants **write**
  to BOTH admin and child across pillars/economy/funds/events/discernment/
  lessons/profiles → a child login is write-capable everywhere by default (the
  reason child logins default to `readonly` below).
- `routes/users.py`: `POST /api/auth/register` is admin-only, bcrypt-hashes,
  409 on duplicate username.
- `config.py`: Secrets Manager used only for admin bootstrap + JWT. No SES/SMTP
  anywhere yet.

---

## Final design

### Schema changes (idempotent boot migration — SQLite ALTER-if-missing)
Add to `users`:
- `email VARCHAR(255) NULL` — delivery/contact only, NOT a login id, not unique
  (one parent email may receive several users' links).
- `must_change_password BOOLEAN NOT NULL DEFAULT 0`
- `setup_token_hash VARCHAR(255) NULL` — SHA-256 of the one-time token
- `setup_token_expires DATETIME NULL`

### Credential delivery — one-time setup link (Option 1)
1. Admin CLI creates the user with a **random throwaway placeholder password**
   (immediately bcrypt-hashed by the existing register endpoint; never shown,
   never transmitted).
2. Generate a 32-byte URL-safe token. Store only its **SHA-256 hash** +
   `setup_token_expires = now + 24h`; set `must_change_password = 1`.
3. Email the user a **link only**: `https://<app-url>/setup?token=<raw-token>`.
   Raw token exists only in the email + transient memory — never logged, never
   persisted raw.
4. User opens link → app validates (hash match, not expired, unused) → user sets
   their own password → app bcrypt-hashes it, clears the token fields, sets
   `must_change_password = 0`.

**Password lifecycle:** the only persisted password form is the bcrypt hash in
`users.hashed_password`. No plaintext anywhere. Token is single-use, ≤24h.

### Child-login handling (opt-in, parent-delivered, read-first)
- Child logins are **NOT auto-issued.** The `child` type creates/links the
  Profile but issues no login unless `--issue-child-login` is passed.
- When issued, the setup link goes to the **parent's** email, never the minor.
- Default issued child login = **`readonly`**. A true write-capable `child` role
  is only created with an explicit `--child-write` flag (per-child, intentional).
  No `auth.py` change needed — this is CLI policy over existing roles.

### Email transport
- **AWS SES** (not app SMTP). The provisioning **CLI** sends via SES using the
  admin's ambient AWS credentials; the running web app **never sends email**, so
  there is no public email-send surface to abuse. No SMTP password is stored
  anywhere.
- Requires: `SES_SENDER` = a verified SES identity to send from; `AWS_REGION`.
  SES is in **sandbox** (can only send to verified addresses) — fine for the
  test case because `<owner-email>` is already a verified identity. Production
  access (sending to arbitrary addresses) is a later, optional request.
- Fallback: `--no-email` prints the one-time setup link to the admin's terminal
  for out-of-band delivery.
- **Email contains:** friendly greeting, the **username**, the role in plain
  terms, the app URL, and the one-time setup link + its expiry.
- **Email omits:** any password/token (except inside the single-use link) and
  **any child PII** (no child name, DOB, milestones, journals).

### New endpoints
- `POST /api/auth/setup-token/{username}` (admin-only): set email + issue a
  setup token for a user. Keeps the CLI from touching the DB directly.
- `GET /setup?token=` + `POST /api/auth/setup` : validate token + set password;
  clear token; drop `must_change_password`.
- Enforce `must_change_password` at login (block normal use until reset).

### The CLI — `provision_user.py` (run locally by the admin)
Authenticates as admin via the login endpoint (no DB/AWS creds embedded).
Args:
- `--type {father|mother|child|visitor}` (required)
- `--username` (required, unique)
- `--display-name` (required)
- `--email` (required unless `--no-email`)
- `--app-url` (required)
- `--issue-child-login` (flag; only with type=child)
- `--child-write` (flag; with issue-child-login → true child role vs readonly)
- `--no-email` (flag; print the setup link to terminal instead of sending)

**Test-case run (father/<admin-username>):**
```
python provision_user.py --type father --username <admin-username> \
  --display-name "..." --email <owner-email> \
  --app-url https://life-planning.my-deployment.com
```
Steps: map father→admin → admin login (JWT) → register <admin-username> with a throwaway
password (409 if exists) → POST setup-token (sets email + token, must_change=1)
→ send_email(<owner-email>, …setup link…) → print non-sensitive confirmation
(username, role, expiry) only.

> Note: `<admin-username>` will be a **second admin** alongside the existing
> Secrets-Manager bootstrap admin — intentional and preferable to sharing the
> bootstrap login.

---

## Build plan

**Phase 1 (build first, test on <owner-email>):**
1. Schema migration (email + must_change_password + setup_token fields).
2. Admin-only `setup-token` endpoint.
3. `send_email()` seam over Gmail SMTP (env-configured). *(Needs a Gmail app
   password — see open item.)*
4. `/setup` page + set-password endpoint; enforce `must_change_password` at login.
5. CLI for `father` + `visitor` types (admin / readonly) with email send +
   `--no-email` fallback.
6. End-to-end test: run the father/<admin-username> command → receive link at
   <owner-email> → set password → log in.

**Phase 2 (after happy path works):**
- `child` type with `--issue-child-login` (readonly default, parent-addressed)
  and `--child-write` opt-in.
- Token resend/expiry UX + nicer email formatting ("well formatted and
  organized" ask).

**Deferred / optional:**
- SES + SPF/DKIM (swap behind the send seam).
- Per-capability child-write hardening in `auth.py`.
- Per-user Secrets Manager entries — **explicitly rejected**, not deferred.

---

## OUTCOME & lessons learned (built + deployed 2026-10-21)

**Status: BUILT, DEPLOYED, and used.** The first account — `pmflani` (role admin,
display name "Patrick Flanigan") — was provisioned on the live app and the SES
setup-link invitation was delivered. Flow verified end-to-end (provision →
emailed one-time link → set own password → login; token single-use).

Implemented: `email`/`must_change_password`/`setup_token_*` columns + idempotent
boot migration; admin-only `POST /api/auth/setup-token/{username}`; public
`POST /api/auth/setup`; login blocks `must_change_password`; `/setup` frontend
page; `email_service.py` (AWS SES); `provision_user.py` CLI. Email is sent ONLY
by the CLI (admin's AWS creds) — the web app never sends mail, so there is no
public email-send surface to abuse.

**Lesson — do NOT send from a `@gmail.com` sender to a Gmail recipient.**
The first invite (from `pmflani@gmail.com` to `pmflani@gmail.com`) sent cleanly
via SES (0 bounces) but Gmail **spam-foldered** it: a message "from a gmail.com
address" that was actually sent via AWS SES fails Gmail's DMARC/spoof check, and
self-to-self is an extra spam signal. **Default for future invites: send FROM a
non-Gmail verified SES identity** (e.g. a ProtonMail/Yahoo identity, or a
verified address on the app's own domain) TO the recipient. Recipient marked the
first one "Not spam," which helps future delivery to that inbox.

---

## Open items / next steps

- [ ] **Slim the Docker image — code only, no docs/tests.** `.dockerignore`
      correctly excludes top-level `docs/`, `diagrams/`, `transcripts/`, etc.,
      BUT the Dockerfile does `COPY app/backend/ ./`, which currently ships
      non-runtime files inside the image: `app/backend/tests/` (pytest suite)
      and `app/backend/.env.example`. (`provision_user.py` is a local admin CLI
      and is also not needed at runtime.) Add `.dockerignore` entries
      (`app/backend/tests/`, `app/backend/.env.example`) or narrow the COPY so
      the runtime image carries only what the app needs. No secrets leak today
      (.env.example is placeholders), but it is bloat + unnecessary surface.
- [ ] **Verify a SES sender on the app's own domain** (or a non-Gmail identity)
      and set it as the default `SES_SENDER` for invitations.
- [ ] **Phase 2 provisioning:** `child` type (`--issue-child-login`, readonly
      default, parent-addressed) and `--child-write` opt-in.
- [ ] Add pytest for token issue/validate/expire + a Playwright test for the
      `/setup` flow (keep the two suites separate).
- [ ] (Optional) Request SES production access to send to non-verified addresses.

---

## One-line summary

One `email` column (+ token fields), four friendly types map onto the three
existing roles, **nobody is emailed a password — they get a 24h one-time link to
set their own**, child logins are opt-in/read-only/sent to the parent, and
Secrets Manager keeps doing only its one admin-bootstrap job. Phase 1 is built,
deployed, and used (admin `pmflani`). Next: slim the Docker image to runtime
code only, and default SES to a non-Gmail sender.

---

## Related follow-ups (added 2026-10-21, phase 2)

- [x] **Build `HEALTH_FORCE_FAIL` toggle** (DONE 2026-10-21, drill verified: banner shown ~97s) so the user-facing failover banner can
      be tested on demand (env var → east returns 503 for health + API → browser
      session fails → banner shows → DNS fails to west → flip back). See
      `deploy/PHASE2_FAILOVER.md` "TWO distinct things to test".
- [x] **Budget** raised to $70/mo and scoped to the `project=life-planning`
      cost-allocation tag (was $50, unfiltered). All 23 phase-1+phase-2 resources
      (15 east + 8 west) tagged `project=life-planning`.

---

## Readonly UX polish (added 2026-10-21)

- A persistent **read-only banner** shows for `readonly` users (role decoded
  from the JWT client-side, for UI hints only — the backend still enforces 403
  on all writes). Write controls tagged `write-action` are dimmed + click-
  disabled via `html[data-role="readonly"]` CSS.
- **Coverage is partial by design:** the banner is always shown (airtight
  messaging), and the primary create/edit entry points (form Save buttons, Sync)
  are disabled. Not every individual inline button is tagged yet — remaining
  write attempts simply fail with the backend's 403. Follow-up: tag the rest
  (per-bounty claim/score/edit/delete, wishlist, fund, attachment controls) for
  full visual coverage.
