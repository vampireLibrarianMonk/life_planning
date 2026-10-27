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
