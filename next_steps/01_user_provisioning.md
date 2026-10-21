# Next Step: User Provisioning & Role Separation

Strategy for adding proper user provisioning (username≠email, three real user
types, secure credential delivery) to the Life Plan Tracker. Decided via an
adversarial design review (Pragmatic Builder vs. Safety Critic → Finalizer).

**Owner decisions locked in:**
- **Delivery mechanism: Option 1** — full one-time **setup link emailed** to the
  user (no password ever emailed or stored in plaintext).
- **Test case:** the father/admin account — username `<admin-username>`,
  email `<owner-email>`, type `father`.

Status: **designed, not yet built.** This is the first thing to pick up next.

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

## Open items to resolve when building

- [ ] **Gmail app password** for SMTP (or decide to start with `--no-email`
      terminal link and wire SMTP second). Store as env/secret, never hardcode.
- [ ] Decide `display_name` for the <admin-username> admin.
- [ ] Confirm the `/setup` page styling matches the app (reuse existing Login
      page look; keep it accessible — a11y suite will check).
- [ ] Add a pytest for token issue/validate/expire and a Playwright test for the
      setup flow (keep the two suites separate, per existing convention).

---

## One-line summary for morning-me

One new `email` column (+ small token fields), four friendly types map onto the
three existing roles, **nobody is emailed a password — they get a 24h one-time
link to set their own**, child logins are opt-in/read-only/sent to the parent,
and Secrets Manager keeps doing only its one admin-bootstrap job. Build Phase 1,
test with `father / <admin-username> / <owner-email>`.
