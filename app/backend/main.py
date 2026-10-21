"""Life Plan Tracker - FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config as app_config
from auth import hash_password
from database import Base, engine, ensure_columns
from models import User
from routes import (
    discernment,
    discernments,
    docs,
    economy,
    events,
    funds,
    lessons,
    pillars,
    profiles,
    users,
)

# Create tables
Base.metadata.create_all(bind=engine)
ensure_columns()  # additive SQLite migration for new User columns

# In AWS (public) mode, do not expose the interactive API explorer / schema.
# Keep them in local dev for convenience.
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None} if app_config.IS_AWS else {}
)
app = FastAPI(title="Life Plan Tracker", version="0.1.0", **_docs_kwargs)

# CORS: in AWS mode, restrict to the app's own origin (the SPA is served
# same-origin by this app, so no cross-origin access is needed). Locally,
# allow any origin for dev convenience.
_allowed_origins = ["https://life-planning.my-deployment.com"] if app_config.IS_AWS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Add defensive response headers (HSTS, CSP, anti-clickjacking, nosniff).

    CSP matters especially because the SPA stores its JWT in localStorage; a
    tight policy is the main barrier between an XSS and token/PII theft.
    """
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' blob: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
    return resp


app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(pillars.router)
app.include_router(economy.router)
app.include_router(events.router)
app.include_router(events.file_router)
app.include_router(docs.router)
app.include_router(discernment.router)
app.include_router(discernments.router)
app.include_router(lessons.router)
app.include_router(funds.router)


@app.on_event("startup")
def seed_admin():
    """Create/align the default admin user from the active config mode.

    Local mode: uses dev defaults (admin/changeme) for frictionless local work.
    AWS mode: pulls admin credentials from Secrets Manager and refuses to boot
    on the insecure default, so the app is never publicly exposed with
    admin/changeme.
    """
    import config
    from database import SessionLocal

    admin_username, admin_password = config.get_admin_credentials()

    if config.IS_AWS and (admin_username == "admin" and admin_password == "changeme"):
        raise RuntimeError(
            "Refusing to start in AWS mode with default admin/changeme credentials. "
            "Set a strong credential in Secrets Manager (ADMIN_SECRET_ARN)."
        )

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == "admin").first()
        if not existing:
            admin = User(
                username=admin_username,
                hashed_password=hash_password(admin_password),
                display_name="Administrator",
                role="admin",
            )
            db.add(admin)
            db.commit()
        elif config.IS_AWS:
            # In AWS mode, keep the admin credential in sync with the secret so
            # rotating the secret rotates the login (idempotent on each boot).
            existing.username = admin_username
            existing.hashed_password = hash_password(admin_password)
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    import config

    return {"status": "ok", "config": config.summary()}


# Serve frontend - must be AFTER api routes
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
else:

    @app.get("/")
    def no_frontend():
        return {
            "message": "API is running. Frontend not built yet.",
            "hint": "cd app/frontend && npm install && npm run build",
            "api_docs": "/docs",
        }
