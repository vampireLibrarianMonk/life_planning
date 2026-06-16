# Software Bill of Materials (SBOM)

**Project:** Life Plan Tracker
**Version:** 0.3.0
**Generated:** 2026-06-15
**License:** Private / Family Use

---

## Runtime Environment

| Component | Version |
|-----------|---------|
| Python | 3.12 |
| Node.js | 22.x (build only) |
| SQLite | 3.x (bundled with Python) |
| Java (PlantUML) | OpenJDK 11+ |

---

## Backend Dependencies (Python)

### Direct Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| fastapi | 0.136.3 | Web framework / API | MIT |
| uvicorn | 0.48.0 | ASGI server | BSD-3 |
| sqlalchemy | 2.0.50 | ORM / database models | MIT |
| pydantic | 2.13.4 | Request/response validation | MIT |
| python-jose | 3.5.0 | JWT token encoding/decoding | MIT |
| bcrypt | 5.0.0 | Password hashing | Apache-2.0 |
| python-multipart | 0.0.30 | Form data parsing | Apache-2.0 |

### Transitive Dependencies

| Package | Version | License |
|---------|---------|---------|
| annotated-types | 0.7.0 | MIT |
| anyio | 4.13.0 | MIT |
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

### Direct Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| react | 18.3.1 | UI library | MIT |
| react-dom | 18.3.1 | DOM rendering | MIT |
| react-router-dom | 6.30.4 | Client-side routing | MIT |

### Dev Dependencies (build only, not shipped)

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| vite | 5.4.21 | Build tool / dev server | MIT |
| @vitejs/plugin-react | 4.7.0 | React JSX transform | MIT |

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
| Uploaded files | `app/backend/uploads/` | Event attachments (images, videos, documents) |
| JWT secret | Environment variable or hardcoded default | Must be changed in production |
| Planning documents | `docs/*.md` | 17 pillar/discernment guides + addenda, served filtered via API (admin only) |

---

## Security Notes

- Passwords are hashed with bcrypt (cost factor 12)
- Authentication uses JWT with 24-hour expiry
- Role-based access control (admin/child/readonly)
- No external network calls — fully self-contained
- SQLite file should be backed up regularly and protected with filesystem permissions
- Default admin password (`changeme`) must be changed after first login

---

## Vulnerability Disclosure

This is a private family application not intended for public deployment. If exposed to a network:
- Change the `SECRET_KEY` environment variable
- Change the default admin password
- Run behind HTTPS (nginx/caddy reverse proxy)
- Restrict network access to trusted devices
