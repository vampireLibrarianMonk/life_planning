"""Database connection and session management."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Default to a file next to the backend; allow override via DATABASE_URL so
# tests (and local experiments) don't clobber the dev database.
DB_PATH = Path(__file__).parent / "life_plan.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns():
    """Idempotent, additive SQLite migration: add any missing columns.

    SQLAlchemy's create_all() creates missing tables but never alters existing
    ones, so new nullable columns on an existing DB must be added here. Safe to
    run on every boot — each ALTER only fires if the column is absent.
    """
    from sqlalchemy import text

    # column_name -> ALTER TABLE ... ADD COLUMN clause
    wanted = {
        "email": "email VARCHAR(255)",
        "must_change_password": "must_change_password INTEGER NOT NULL DEFAULT 0",
        "setup_token_hash": "setup_token_hash VARCHAR(255)",
        "setup_token_expires": "setup_token_expires DATETIME",
        "token_version": "token_version INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
        for col, clause in wanted.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {clause}"))

        # discernment_journal.created_by: author of each reflection. Existing
        # rows default to 'child' (treat pre-existing reflections as the child's
        # private diary) so parents cannot retroactively read them.
        dj_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(discernment_journal)"))}
        if dj_cols and "created_by" not in dj_cols:
            conn.execute(
                text(
                    "ALTER TABLE discernment_journal "
                    "ADD COLUMN created_by VARCHAR(20) NOT NULL DEFAULT 'child'"
                )
            )
