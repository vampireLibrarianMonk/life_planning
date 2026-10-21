"""User management and authentication routes."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    hash_password,
    require_admin,
    verify_password,
)
from database import get_db
from models import User
from schemas import (
    LoginRequest,
    SetPasswordRequest,
    SetupTokenRequest,
    SetupTokenResponse,
    Token,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/login", response_model=Token)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.must_change_password:
        # Account exists but the setup link hasn't been used to set a password.
        raise HTTPException(
            status_code=403,
            detail="Password setup required. Use the setup link from your invitation email.",
        )
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


@router.post("/register", response_model=UserResponse)
def register_user(
    req: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        display_name=req.display_name,
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/setup-token/{username}", response_model=SetupTokenResponse)
def issue_setup_token(
    username: str,
    req: SetupTokenRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin-only: set a user's email and issue a one-time setup token.

    Returns the RAW token to the caller (the provisioning CLI), which emails the
    setup link. Only the SHA-256 hash is stored; the raw token is never
    persisted or logged. Flags the account must_change_password.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    raw = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(hours=max(1, req.expires_hours))
    if req.email:
        user.email = req.email
    user.setup_token_hash = _hash_token(raw)
    user.setup_token_expires = expires
    user.must_change_password = 1
    db.commit()
    db.refresh(user)
    return {
        "username": user.username,
        "role": user.role,
        "setup_token": raw,
        "expires_at": expires,
    }


@router.post("/setup")
def complete_setup(req: SetPasswordRequest, db: Session = Depends(get_db)):
    """Public: validate a one-time setup token and set the user's password."""
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    token_hash = _hash_token(req.token)
    user = db.query(User).filter(User.setup_token_hash == token_hash).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or already-used setup link")

    expires = user.setup_token_expires
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires is None or datetime.now(UTC) > expires:
        raise HTTPException(status_code=400, detail="This setup link has expired")

    user.hashed_password = hash_password(req.new_password)
    user.setup_token_hash = None
    user.setup_token_expires = None
    user.must_change_password = 0
    db.commit()
    return {"detail": "Password set. You can now log in.", "username": user.username}
