# Software Bill of Materials (SBOM)

**Project:** Life Plan Tracker
**Version:** 0.5.1
**Generated:** 2026-07-10

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

| Package | Pinned | Installed | Purpose | License |
|---------|--------|-----------|---------|---------|
| fastapi | 0.115.0 | 0.136.3 | Web framework / API | MIT |
| uvicorn[standard] | 0.30.0 | 0.48.0 | ASGI server | BSD-3 |
| sqlalchemy | 2.0.35 | 2.0.50 | ORM / database models | MIT |
| pydantic | 2.9.0 | 2.13.4 | Request/response validation | MIT |
| python-jose[cryptography] | 3.3.0 | 3.5.0 | JWT token encoding/decoding | MIT |
| passlib[bcrypt] | 1.7.4 | 1.7.4 | Password hashing (bcrypt backend) | BSD-3 |
| python-multipart | 0.0.9 | 0.0.30 | Form data / file upload parsing | Apache-2.0 |
| alembic | 1.13.0 | — | DB migrations (listed but unused) | MIT |

Note: Pinned versions in `requirements.txt` are floor pins. The installed versions are what's actually running after `pip install -r requirements.txt` resolves latest compatible versions.

### Transitive Dependencies (installed)

| Package | Version | License |
|---------|---------|---------|
| annotated-types | 0.7.0 | MIT |
| anyio | 4.13.0 | MIT |
| bcrypt | 5.0.0 | Apache-2.0 |
| click | 8.4.1 | BSD-3 |
| ecdsa | 0.19.2 | MIT |
| greenlet | 3.5.1 | MIT |
| h11 | 0.16.0 | MIT |
| idna | 3.18 | BSD-3 |
| pyasn1 | 0.6.3 | BSD-2 |
| pydantic_core | 2.46.4 | MIT |
| rsa | 4.9.1 | Apache-2.0 |
| six | 1.17.0 | MIT |
| starlette | 1.2.1 | BSD-3 |
| typing-inspection | 0.4.2 | MIT |
| typing_extensions | 4.15.0 | PSF |

---

## Frontend Dependencies (JavaScript)

### Direct Dependencies (`package.json`)

| Package | Spec | Installed | Purpose | License |
|---------|------|-----------|---------|---------|
| react | ^18.3.1 | 18.3.1 | UI library | MIT |
| react-dom | ^18.3.1 | 18.3.1 | DOM rendering | MIT |
| react-router-dom | ^6.26.0 | 6.30.4 | Client-side routing | MIT |
| react-easy-crop | ^5.1.0 | 5.1.0 | Avatar image cropping | MIT |

### Dev Dependencies (build only, not shipped)

| Package | Spec | Installed | Purpose | License |
|---------|------|-----------|---------|---------|
| vite | ^5.4.0 | 5.4.21 | Build tool / dev server | MIT |
| @vitejs/plugin-react | ^4.3.1 | 4.7.0 | React JSX transform | MIT |

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
| JWT secret | Environment variable or hardcoded default | Must be changed in production |
| Planning documents | `docs/*.md` | 25 pillar/discernment/program guides + addenda, served filtered via API (admin only) |

---

## Application Metrics

| Metric | Value |
|--------|-------|
| Seeded milestones | 540 |
| Seeded bounties | 136 |
| Pillars | 14 |
| Programs | 10 (all populated) |
| Discernment categories | 10 |
| Bounty tiers | 10 (Bronze → Ironforged) |
| Planning documents | 25 + IMPLEMENTATION_NOTES |
| API routes | 69 |

---

## Security Notes

- Passwords are hashed with passlib/bcrypt (cost factor 12)
- Authentication uses JWT with 24-hour expiry
- Role-based access control: admin (full CRUD), child (own profile + bounties), readonly (view only — enforced at API level)
- No external network calls — fully self-contained
- SQLite file should be backed up regularly (`POST /api/profiles/backup`) and protected with filesystem permissions
- Default admin password (`changeme`) must be changed after first login

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
| alembic | Listed in requirements.txt, not installed, not used | No alembic.ini or migrations/ directory exists. Can be removed from requirements.txt when convenient. |
