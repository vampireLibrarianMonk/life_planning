"""User management and authentication routes."""

import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
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

# --- Lightweight in-memory login throttle (defense-in-depth) -----------------
# App Runner is pinned to a single instance, so a process-local sliding window
# is effective (it resets on redeploy, which is acceptable for a tiny family
# app). This complements, not replaces, a WAF rate-based rule. No new deps.
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes
_login_attempts: dict[str, list[float]] = {}


def _login_throttle(key: str) -> None:
    now = time.monotonic()
    cutoff = now - _LOGIN_WINDOW_SECONDS
    hits = [t for t in _login_attempts.get(key, []) if t > cutoff]
    if len(hits) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please wait a few minutes and try again.",
        )
    hits.append(now)
    _login_attempts[key] = hits
    # Opportunistic cleanup so the dict can't grow unbounded.
    if len(_login_attempts) > 1000:
        for k in [k for k, v in _login_attempts.items() if not any(t > cutoff for t in v)]:
            _login_attempts.pop(k, None)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/login", response_model=Token)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Throttle by client IP + attempted username (defense-in-depth vs. brute force).
    client_ip = request.client.host if request.client else "unknown"
    _login_throttle(f"{client_ip}:{req.username}")

    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        # Uniform response whether the username exists or the password is wrong
        # (no user-enumeration signal). The setup hint is appended generically so
        # it doesn't confirm a specific account exists.
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid credentials. If you were invited and haven't set a "
                "password yet, use the setup link from your invitation email."
            ),
        )
    if user.must_change_password:
        # Account exists but the setup link hasn't been used — same generic 401
        # (don't distinguish this state from a wrong password to avoid enumeration).
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid credentials. If you were invited and haven't set a "
                "password yet, use the setup link from your invitation email."
            ),
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
