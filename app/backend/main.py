"""Life Plan Tracker - FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config as app_config
from auth import hash_password
from database import Base, engine, ensure_columns
from models import User
from routes import (
    archive,
    child_development,
    demo,
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
    """Add defensive response headers + a server-side CSRF (Origin) check.

    The JWT is carried in an httpOnly `SameSite=strict` cookie, so the browser
    already withholds it cross-site. This middleware adds a SECOND, server-side
    CSRF barrier (independent of SameSite): for unsafe methods, if an `Origin`
    header is present it must match an allowed origin, else the request is
    rejected. Same-origin SPA calls always send a matching Origin, so this is
    transparent to real use but blocks cross-site forged POST/PATCH/PUT/DELETE.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin is not None and origin not in _allowed_origins and _allowed_origins != ["*"]:
            return JSONResponse(
                status_code=403, content={"detail": "Cross-origin request blocked."}
            )

        # Coarse request-body-size cap (defense against memory-exhaustion DoS on
        # the single App Runner instance). Upload routes get a higher ceiling;
        # all other bodies are small JSON. Rejects early on declared length.
        _p = request.url.path
        _is_upload = (
            _p.endswith("/attachments/") or _p.endswith("/avatar") or _p.endswith("/restore")
        )
        _max_bytes = (50 * 1024 * 1024) if _is_upload else (1 * 1024 * 1024)
        _cl = request.headers.get("content-length")
        if _cl is not None:
            try:
                if int(_cl) > _max_bytes:
                    return JSONResponse(
                        status_code=413, content={"detail": "Request body too large."}
                    )
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Bad Content-Length."})

    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # Authenticated API responses carry child PII / financial data — never cache.
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        # Images/media: self + data/blob (avatar crop preview) + the S3 hosts the
        # blob route 307-redirects to (presigned URLs). Dropped blanket https: so
        # an injected <img src=https://attacker/?leak> can't beacon out.
        "img-src 'self' data: blob: https://*.s3.amazonaws.com "
        "https://*.s3.us-east-1.amazonaws.com https://*.s3.us-west-2.amazonaws.com; "
        "media-src 'self' blob: https://*.s3.amazonaws.com "
        "https://*.s3.us-east-1.amazonaws.com https://*.s3.us-west-2.amazonaws.com; "
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
app.include_router(demo.router)
app.include_router(archive.router)
app.include_router(child_development.router)


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
            # Do NOT clobber the admin password on every boot — that silently
            # reverted any in-app password change and could diverge across
            # regions mid-rotation. Seed-if-absent is the default. To roll a
            # rotated secret onto the account, the operator sets ADMIN_FORCE_SYNC=1
            # for one deploy (explicit, auditable), then removes it.
            import os

            if os.getenv("ADMIN_FORCE_SYNC") == "1":
                existing.username = admin_username
                existing.hashed_password = hash_password(admin_password)
                db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    import os

    from fastapi.responses import JSONResponse

    import config

    # Drill switch: when HEALTH_FORCE_FAIL=1, report unhealthy (503). This makes
    # BOTH the Route 53 health check and the browser's /api/health poll fail, so
    # a real user-facing failover (and the RegionFailoverBanner) can be tested on
    # demand. Set back to 0 (or unset) to recover. Default is healthy.
    if os.getenv("HEALTH_FORCE_FAIL", "0") == "1":
        return JSONResponse(
            status_code=503,
            content={"status": "forced_fail", "config": config.public_summary()},
        )
    return {"status": "ok", "config": config.public_summary()}


@app.get("/api/alive")
def alive():
    """Liveness probe for App Runner's deployment health check ONLY.

    Always 200 while the process is up — unaffected by HEALTH_FORCE_FAIL — so a
    failover drill (which makes /api/health 503) does not cause App Runner to
    roll the deployment back. Route 53 + the browser banner watch /api/health;
    App Runner's service health check watches /api/alive.
    """
    return {"status": "alive"}


# Serve frontend - must be AFTER api routes
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = (FRONTEND_DIR / full_path).resolve()
        # Path-containment guard: only serve files that actually resolve INSIDE
        # the dist dir (defense against ../ escaping the build output).
        try:
            inside = file_path.is_relative_to(FRONTEND_DIR.resolve())
        except AttributeError:  # Python <3.9 fallback (not expected on 3.12)
            inside = str(file_path).startswith(str(FRONTEND_DIR.resolve()))
        if inside and file_path.is_file():
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
