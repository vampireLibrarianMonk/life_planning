"""Life Plan Tracker - FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import Base, engine
from models import User
from auth import hash_password
from routes import users, profiles, pillars, economy, events, docs, discernment, discernments, lessons
from routes import funds

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Life Plan Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Create default admin user if none exists."""
    from database import SessionLocal

    db = SessionLocal()
    if not db.query(User).filter(User.role == "admin").first():
        admin = User(
            username="admin",
            hashed_password=hash_password("changeme"),
            display_name="Administrator",
            role="admin",
        )
        db.add(admin)
        db.commit()
    db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


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
