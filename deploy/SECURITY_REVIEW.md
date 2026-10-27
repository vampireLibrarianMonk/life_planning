# Life Plan Tracker — Security Review

_Assembled 2026-10-27 from the repository, commit history, and deployment state.
This is the baseline document for a 3-agent security re-review. Every claim below
is grounded in code/config in this repo; file references are given so reviewers
can verify._

---

## 1. System summary

- **What:** a private, invite-only family web app tracking a child's lifetime
  development (pillars, family economy/bounties, discernment journals, early
  childhood "Child Development", life maps).
- **Stack:** FastAPI (Python 3.12) + React/Vite SPA, SQLite (`life_plan.db`),
  attachments in S3 (AWS) or local disk (dev). Single Docker image serves the
  built SPA + API same-origin.
- **Deploy:** AWS App Runner, dual-region (us-east-1 primary / us-west-2 warm
  standby), Route 53 failover, behind AWS WAF, custom domain with managed TLS.
- **Users/roles:** `admin` (parents), `child` (the child, scoped to own
  profile), `readonly` (extended family, view-only). ~7 real accounts.
- **Sensitive assets:** children's PII (name, DOB, **photos/videos**), the
  **behavior-incident log**, **private discernment journals**, **financial
  totals**, and account credentials/email.

---

## 2. Authentication

- **Password hashing:** bcrypt via `passlib`/`bcrypt` (`auth.hash_password` /
  `verify_password`). No plaintext passwords stored or emailed.
- **Sessions:** JWT (HS256), signing key from Secrets Manager in AWS
  (`config.get_jwt_secret`; `auth.py:15-17`). **TTL 2 hours**
  (`ACCESS_TOKEN_EXPIRE_MINUTES = 120`) — short-lived by design.
- **Account provisioning:** admins never set/receive a password. New users get a
  **one-time, 72h setup link** (hashed token stored, not the raw token);
  `must_change_password` blocks login until setup completes.
- **Default-credential guard:** in AWS mode the app **refuses to boot** with the
  `admin`/`changeme` default (`config.get_admin_credentials` raises
  `RuntimeError` if the secret is missing); admin creds are sourced from Secrets
  Manager and re-synced on boot. (Test: `tests/test_auth_hardening.py`.)
- **Token storage (KNOWN RISK):** the SPA stores the JWT in `localStorage`, which
  is readable by any XSS. Mitigated — not eliminated — by a strict CSP (§5) and
  short token TTL. Documented in `main.py` security-headers comment. Candidate
  for future hardening (httpOnly cookie + CSRF).

---

## 3. Authorization / access control (the core of this app's security)

Role + per-profile guards in `auth.py`, applied as FastAPI dependencies
(router-level where possible). Guard matrix:

| Guard | Admits | Rejects | Used for |
|---|---|---|---|
| `require_admin` | admin | child, readonly | user mgmt, profile create/delete, backups, lessons |
| `require_admin_or_child` | admin, child | readonly | all write operations (readonly is view-only) |
| `require_profile_access` | admin, readonly, **owning** child | **non-owning child**, ungranted others | router-level on every `/profiles/{id}/...` route |
| `require_private_profile_access` | admin, **owning** child | readonly, non-owning child | behavior log, journals, financial totals, CD worries |
| `require_private_access` | admin, child | readonly | (legacy; superseded by the profile-aware variant) |

**Key invariants, each backed by a fix + regression test:**

1. **Readonly is view-only.** All writes depend on `require_admin_or_child`;
   readonly gets 403. Frontend also hides CRUD controls + shows a role banner
   and a 403 toast (defense-in-depth, not the boundary). Regression:
   `tests/test_readonly_enforcement.py` enumerates every mutating route and
   asserts a readonly-blocking guard. (Commits `064464f`, `75d3a04`.)

2. **Child cannot self-deal.** Behavior-incident create/delete and bounty
   `paid` transitions are admin-only — a child can't score their own behavior or
   pay themselves. (Commit `75d3a04`; `routes/economy.py`.)

3. **Cross-child isolation (FIXED vulnerability).** Profile-scoped sub-resource
   routes previously checked only *role*, not *ownership* — a child could read
   another child's data by changing the URL id (verified exploitable, then
   fixed). `require_profile_access` is now a **router-level dependency on all 7
   profile-scoped routers** (pillars, economy, funds, lessons, discernment,
   discernments, events). Regression tests assert a non-owning child + readonly
   get 403. (Commit `a4db463`.)

4. **Private-by-design data.** Behavior log, discernment journals, and aggregate
   financial totals use `require_private_profile_access` (admin + owning child
   only; **readonly excluded**). The discernment journal is further an
   author-scoped diary: a child's reflections are invisible to admin; admin sees
   only admin-authored notes. `/eligibility` returns tier-only for readonly (no
   per-trait behavior breakdown). (Commits `f6f5480`, `14a49f9`, `6edbe55`.)

5. **Public demo isolation.** `/demo` + `/api/demo/*` serve 100% static
   in-memory fake data and never touch the DB, so no real profile can leak via
   the demo. (`routes/demo.py`.)

**Known / accepted:** admin and readonly have **household-wide** access to all
profiles (single-family model, owner-accepted). `ProfileAccess`-based per-profile
scoping exists for "other" roles and is the hook to tighten this before any
non-family user is added. Child Development objectives + accomplishment photos
are intentionally **family-readable**; only the "worries" note is parent/child
private.

---

## 4. Data protection

- **Encryption at rest:** S3 uploads + the SQLite DB stream (Litestream) are
  SSE-KMS encrypted with a customer-managed multi-region KMS key
  (`alias/life-planning-mr`). Uploads bucket: Block Public Access, versioning,
  SSE-KMS default, **TLS-only bucket policy** (non-HTTPS denied).
  (`deploy/SECURITY_GATES.md` steps 2-3.)
- **Encryption in transit:** HTTPS end-to-end via App Runner managed TLS on the
  custom domain; HSTS header set (§5).
- **Attachment serving:** S3 objects served via short-lived SigV4 presigned URLs
  (SigV4 required for the KMS bucket; commit `a3a5806`). Local mode serves via
  the app's own route.
- **Secrets:** admin creds + JWT secret in Secrets Manager (replicated to the
  standby region); never in the repo. `.arn-env` (git-ignored) holds resource
  IDs only. Source reference PDFs live in a git-ignored `reference/` folder.
- **Backup / delete:** profile **archive** (zip of per-domain JSON + blobs) with
  a **signed one-time token handshake** required before a **full-clean delete**
  (removes DB rows *and* storage blobs). Restore preserves IDs, fails on
  conflict. (Commit `e5ea0b9`; `routes/archive.py`;
  `tests/test_delete_profile.py` round-trip.)

---

## 5. Network / transport / headers

- **AWS WAF** regional web ACL attached to the service; allow-lists `/api/health`
  and the SPA; blocks unexpected paths. (`deploy/SECURITY_GATES.md` step 6.)
- **Security headers** (middleware, `main.py`): `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, **HSTS**
  (1 year + subdomains), and a **Content-Security-Policy** (`default-src 'self'`,
  `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'`). CSP is the
  primary barrier between an XSS and localStorage-token theft.
- **CORS:** in AWS mode restricted to the app's own origin with
  `allow_credentials=False`; wildcard only in local dev.
- **API docs disabled in production:** `docs_url`/`redoc_url`/`openapi_url` are
  `None` when `IS_AWS` (no public schema surface). (Commit `4e0b513`.)

---

## 6. Email security (SES)

- Sends only from the **DKIM-aligned domain** `no-reply@life-planning.my-deployment.com`
  (Easy DKIM + custom MAIL FROM + `_dmarc` record, both regions). Fixed a real
  DMARC-fail bounce caused by the earlier `@proton.me` sender. (Commits `0ee46c7`,
  `7ef2d5e`.) Invitations carry no password and a 72h expiry.
- The web app never sends email — only the local `provision_user.py` CLI does, so
  there is no public email-send surface to abuse.

---

## 7. Supply chain / SDLC

- **Pre-commit security gate:** `detect-private-key`, **gitleaks**, **bandit**
  (Python SAST), **pip-audit** (Python CVEs), **npm audit** (frontend prod deps,
  outage-tolerant), **hadolint** (Dockerfile), plus ruff/mypy.
- **Tests:** backend suite incl. dedicated security tests
  (`test_auth_hardening`, `test_readonly_enforcement`, `test_child_development`,
  `test_delete_profile`, `test_storage`); Playwright a11y + walkthrough e2e.
- **Images:** Docker build excludes tests/CLI/.env via `.dockerignore`; runtime
  deps pinned; runtime venv mirrors the image.
- **Least privilege:** App Runner instance role grants only read of the two
  secrets, the uploads bucket, the one KMS key, and its own logs.

---

## 8. Known risks / open items (for the review to weigh)

| # | Item | Severity (self-assessed) | Status |
|---|---|---|---|
| R1 | JWT in `localStorage` (XSS → token/PII theft) | Medium | Mitigated by CSP + 2h TTL; cookie+CSRF is the real fix — **open** |
| R2 | Admin + readonly see ALL profiles (no per-profile scoping) | Low (single family) | Accepted; `ProfileAccess` path exists for future non-family users |
| R3 | `require_private_access` (legacy, role-only) still defined | Low | Superseded by profile-aware guard; consider removing to avoid misuse |
| R4 | Archive/restore round-trip for Child Development `*_private` rows + photos | Low | Generic path covers it; **add an explicit round-trip assertion** |
| R5 | `child` role can write (claim bounties, edit own milestones) | Low (by design) | Intended; worth confirming the child account's blast radius |
| R6 | Lessons responses are parent-visible (not child-private) | Low | Intentional (future LLM eval); documented decision |
| R7 | Uploaded blobs orphaned only if delete runs without archive token | Low | Full-clean delete removes blobs; archive handshake enforced |

---

## 9. What this review should scrutinize (handoff to the 3-agent panel)

1. **Access-control correctness** — are the five guards applied to *every*
   sensitive route, with no gap (esp. any new Child Development routes)? Is the
   cross-child fix complete across all 7 routers + the archive/demo/CD routes?
2. **Token/XSS posture** — is CSP actually tight enough given `localStorage`
   JWT + user-uploaded images/`unsafe-inline` styles? Is R1 worth fixing now?
3. **Data-at-rest/secrets/IAM** — least-privilege role scope, KMS key policy,
   secret rotation story, and whether anything sensitive can reach logs.
4. **Tenant isolation & privacy invariants** — can any role (esp. readonly or a
   second child) reach another child's behavior log / journals / financial
   totals / photos by any route, parameter, or the archive/restore path?

---

## 10. Re-review results (3-agent panel, 2026-10-27) + remediation

The panel (access-control, appsec/web, cloud/infra) ran against this doc + live
code. Summary of findings and what was done.

### Fixed in code (this pass) — all test-covered, additive, reversible
- **CRITICAL — unauthenticated blob access (the real one).** `/api/uploads/{key}`
  served any attachment/avatar with **zero auth** and (in AWS) minted a presigned
  URL for anyone — a readonly grandparent or a second child could fetch another
  child's photos by filename. **Fixed:** `serve_upload` now requires a valid JWT
  (via `?token=` since `<img>` tags can't send headers), resolves the file's
  owning profile, and applies the same per-profile access rule; unknown/bad/
  unauthorized/path-escape all return **404** (no oracle). Local serving now
  forces `Content-Disposition: attachment` + `application/octet-stream` so a
  malicious HTML/SVG upload can't execute in the app origin. Frontend fetches via
  a new `uploadUrl()` helper that appends the token. Tests:
  `tests/test_upload_authz.py` (7).
- **HIGH — `/restore` path traversal + blob overwrite.** A crafted archive could
  write `uploads/../x` (local path escape) or overwrite another profile's live
  blob. **Fixed:** reject upload keys containing `/`, `\`, or `..` (400) and
  refuse to overwrite an existing stored key (409). Tests in
  `tests/test_delete_profile.py`.
- **LOW/infra-code — `/api/health` info leak.** The unauthenticated health route
  echoed the uploads bucket name + secrets source. **Fixed:** added
  `config.public_summary()` (mode + region only) for the public route; the
  verbose `summary()` is now logging-only.

### Confirmed SAFE by the panel (no change needed)
- **XSS / crown-jewel path is clean** — `MiniMarkdown` and all rendering go
  through React auto-escaping; **no `dangerouslySetInnerHTML`/innerHTML anywhere**.
  The `localStorage` JWT risk stays gated behind "never add an HTML sink."
- **JWT alg handling safe** — `decode(..., algorithms=["HS256"])` pins the alg
  (no `alg:none`/confusion).
- **Router-level `require_profile_access`** does run on every included route, so
  the bare-`get_current_user` GETs under those routers are still profile-scoped.
- **`profiles` GET `/{id}`** correctly 404s a child on a non-owned profile.
- **Archive token** is not forgeable (HS256, server secret, profile-bound).

### Deferred — documented, NOT changed while unattended (owner decision)
_Update 2026-10-27 (second pass, owner pre-approved): most of these are now DONE
in code; only the cookie migration remains deferred (deliberately)._
- ✅ **Single-use / replay hardening of the archive token.** Token TTL cut 30→10
  min and now **bound to the acting user id** (`uid` claim) — a leaked token is
  short-lived and unusable by a different account. (Full single-use `jti` state
  still skipped — needs cross-region storage; the binding + short TTL cover the
  practical risk.) Tests in `tests/test_delete_profile.py`.
- ✅ **Login user-enumeration.** The pre-setup case now returns the SAME generic
  401 as a wrong password (no distinguishing 403), with a generic setup hint
  that doesn't confirm a specific account. (`routes/users.py`.)
- ✅ **Login rate limiting (in-app).** Process-local sliding-window throttle on
  `/api/auth/login` (10 attempts / 5 min per IP+username → 429). Effective given
  the single-instance App Runner pin; complements (not replaces) a WAF rate rule.
  Tests: `tests/test_login_throttle.py`.
- ✅ **`no-danger` guardrail.** New pre-commit hook fails the build if
  `dangerouslySetInnerHTML`/`innerHTML`/`insertAdjacentHTML`/`document.write`
  is ever introduced in the SPA — permanently gates the localStorage-JWT risk.
- ⏸️ **R1 localStorage JWT → httpOnly cookie + CSRF — STILL DEFERRED (on purpose).**
  This is a high-blast-radius auth rewrite (cookie set/read, CSRF tokens on all
  state-changing routes, and it interacts with the new blob `?token=` scheme); a
  mistake could lock out all users. The appsec agent explicitly advised against a
  reactive migration, and residual risk is low now (clean XSS path + no-danger
  lint + 2h TTL + tight CSP). **To be done WITH the owner present** so login /
  logout / image-loading can be verified end-to-end before it goes live.

### Owner-required infra checklist (NOT touched while unattended)
_Update 2026-10-27 — read-only verification done; one real finding surfaced._
1. **WAF — ⚠️ FINDING: us-west-2 standby appears to have NO web ACL.** Verified
   live: `life-planning-waf` exists + (presumed) attached in **us-east-1**, but
   `wafv2 list-web-acls --scope REGIONAL --region us-west-2` returns **empty**.
   On a regional failover, the standby would serve traffic **without WAF**
   (rate-limiting/managed rules bypassed). **Priority fix on return:** create the
   same web ACL in us-west-2 and attach it to the west App Runner service; add a
   rate-based rule on `/api/auth/login`. (Not done unattended — a misconfigured
   WAF can black-hole the standby.)
2. **KMS — ✅ VERIFIED multi-region.** `alias/life-planning-mr` →
   `mrk-4e4cf93c38474f2d8bb7e294180eb6f0`, MultiRegion=true, Enabled. Still
   confirm the west replica key + that west can decrypt on failover, and the key
   policy is decrypt-to-role-only / no wildcards.
3. **Secrets** — establish rotation for admin + JWT secrets (per-process
   `lru_cache` ⇒ takes effect on redeploy); CloudTrail alert on `GetSecretValue`
   by any non-instance principal. (Not done unattended — rotation invalidates
   live tokens.)
4. **IAM** — instance-role S3/KMS scoped (no `*`); `house-user` MFA + stale-key
   rotation; root MFA/no-root-keys; CloudTrail multi-region on. (Not unattended —
   lockout risk.)
5. **CloudWatch** — log-group retention + KMS encryption; confirm uvicorn access
   logs don't capture query-string PII (headers/bodies not logged by default).
6. **S3/DR** — confirm Litestream restore window; ensure the least-priv role
   cannot delete object versions / change versioning (consider Object Lock).
   (Not unattended — a wrong deny can block recovery.)
7. **Budgets — ✅ already in place** (`life-planning-monthly`, $70/mo cap). A
   billing *alarm* with SNS notification is the only add still worth doing (left
   for owner since it touches SNS subscriptions).
