# Software Bill of Materials (SBOM)

**Project:** Life Plan Tracker
**Version:** 0.6.0
**Generated:** 2026-10-31

---

## Runtime Environment

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| Node.js | 22.x (build only) |
| SQLite | 3.x (bundled with Python) |
| Java (PlantUML) | OpenJDK 11+ (diagram rendering only) |

---

## Backend Dependencies (Python)

### Direct Dependencies (`requirements.txt`)

Versions are **exact pins** (`==`) — the running version equals the pin.

| Package | Pinned | Purpose | License |
|---------|--------|---------|---------|
| fastapi | 0.118.3 | Web framework / API | MIT |
| uvicorn[standard] | 0.30.0 | ASGI server | BSD-3 |
| sqlalchemy | 2.0.35 | ORM / database models | MIT |
| pydantic | 2.9.0 | Request/response validation | MIT |
| PyJWT | 2.15.0 | JWT encode/decode (HS256) | MIT |
| passlib[bcrypt] | 1.7.4 | (pinned but UNUSED — auth.py uses raw `bcrypt`; dead dep) | BSD-3 |
| python-multipart | 0.0.31 | Form data / file upload parsing | Apache-2.0 |
| alembic | 1.13.0 | (listed but unused — no migrations/ dir) | MIT |
| boto3 | 1.35.76 | AWS SDK (S3 + Secrets Manager, AWS mode) | Apache-2.0 |

> **2026-10-31:** `python-jose[cryptography]` was **removed** and replaced with
> **PyJWT 2.15.0** (stale-advisory + transitive ecdsa/pyasn1 cleanup). JWT uses
> HS256 only, with `algorithms=["HS256"]` pinned on decode.

### Transitive Dependencies (notable)

| Package | License | Notes |
|---------|---------|-------|
| bcrypt | Apache-2.0 | password hashing (used directly by auth.py) |
| annotated-types | MIT | pydantic |
| anyio | MIT | starlette/async |
| click | BSD-3 | uvicorn CLI |
| h11 | MIT | uvicorn HTTP |
| idna | BSD-3 | |
| pydantic_core | MIT | pydantic (Rust) |
| starlette | BSD-3 | FastAPI core |
| typing_extensions | PSF | |

> The former python-jose transitive deps (**ecdsa, rsa, pyasn1, six**) are **no
> longer present** after the PyJWT migration — PyJWT has no such dependencies.

---

## Frontend Dependencies (JavaScript)

### Direct Dependencies (`package.json`)

| Package | Spec | Installed | Purpose | License |
|---------|------|-----------|---------|---------|
| react | ^18.3.1 | 18.3.1 | UI library | MIT |
| react-dom | ^18.3.1 | 18.3.1 | DOM rendering | MIT |
| react-router-dom | ^7.18.4 | 7.18.4 | Client-side routing | MIT |
| react-easy-crop | ^5.1.0 | 5.1.0 | Avatar image cropping | MIT |

### Dev Dependencies (build/test only, not shipped)

| Package | Spec | Installed | Purpose | License |
|---------|------|-----------|---------|---------|
| vite | ^7.3.7 | 7.3.7 | Build tool / dev server | MIT |
| @vitejs/plugin-react | ^5.2.0 | 5.2.0 | React JSX transform | MIT |
| @playwright/test | ^1.55.1 | 1.55.1 | Browser e2e / walkthrough testing | Apache-2.0 |
| @axe-core/playwright | ^4.10.2 | 4.10.2 | Accessibility (WCAG) scanning | MPL-2.0 |

---

## Diagram Tooling (optional, not runtime)

| Tool | Version | Purpose | License |
|------|---------|---------|---------|
| PlantUML | 1.2024.8 | Diagram rendering from .puml files | GPL-3.0 |
| OpenJDK | 11+ | Java runtime for PlantUML | GPL-2.0+CE |

---

## Data Storage

| Component | Location | Sensitivity |
|-----------|----------|-------------|
| SQLite database | `app/backend/life_plan.db` | Contains child PII (name, DOB), behavior incidents, financial data, bounty history, discernment reflections |
| Database backups | `app/backend/backups/` | Timestamped copies (last 10 retained) |
| Uploaded files | `app/backend/uploads/` | Event attachments (images, videos, documents) |
| JWT secret | AWS Secrets Manager (AWS mode) / `SECRET_KEY` env (local) | AWS mode **refuses to boot** without `JWT_SECRET_ARN`; no hardcoded prod default |
| Planning documents | `docs/*.md` | 25 pillar/discernment/program guides + addenda, served filtered via API (admin only) |

> **Runtime binary:** Litestream v0.3.13 (Apache-2.0) is downloaded in the
> Docker build (SHA256-verified) for continuous SQLite→S3 replication.

---

## Application Metrics

| Metric | Value |
|--------|-------|
| Seeded milestones | 590 |
| Seeded bounties | 209 |
| Pillars | 14 |
| Programs | 10 (all populated) |
| Discernment categories | 10 |
| Bounty tiers | 10 (Bronze → Ironforged) |
| Planning documents | 25 + IMPLEMENTATION_NOTES |
| API routes | 69 |

---

## Security Notes

- Passwords are hashed with **bcrypt** directly (`bcrypt.gensalt()`, default cost
  factor 12); input is truncated to bcrypt's 72-byte limit. (passlib is pinned
  but no longer used.)
- Authentication uses a **JWT (HS256, 2-hour expiry)** carried in an **httpOnly,
  `SameSite=strict`, `Secure` cookie** (`lp_auth`), cookie-first with a Bearer
  header fallback; a `token_version` claim enables instant revocation
  (logout / password change). The token is **not** readable by JS.
- Role-based access control: admin (full CRUD), child (own profile + bounties),
  readonly (view only — enforced at API level via router-level guards).
- No external network calls at request time; AWS mode uses S3 + Secrets Manager
  via the instance role.
- SQLite is continuously replicated to S3 (Litestream) with S3 Object Lock
  (GOVERNANCE/7d) on the backup buckets; local backups via `POST /api/profiles/backup`.
- **AWS mode refuses to boot** with the default `admin`/`changeme` credentials
  (sourced from Secrets Manager instead).

---

## Vulnerability Disclosure

This is a private family application not intended for public deployment. If exposed to a network:
- Change the `SECRET_KEY` environment variable
- Change the default admin password
- Run behind HTTPS (nginx/caddy reverse proxy)
- Restrict network access to trusted devices

---

## Dead Dependencies

| Package | Status | Notes |
|---------|--------|-------|
| alembic | Listed in requirements.txt, unused | No `alembic.ini` or `migrations/` directory. Schema changes use the additive `ensure_columns()` migration in `database.py`. Removable. |
| passlib[bcrypt] | Listed in requirements.txt, unused | `auth.py` hashes with raw `bcrypt` directly; passlib is not imported anywhere. Removable. |
