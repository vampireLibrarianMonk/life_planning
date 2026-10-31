"""User management and authentication routes."""

import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_COOKIE_NAME,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from config import IS_AWS
from database import get_db
from models import User
from schemas import (
    ChangePasswordRequest,
    LoginRequest,
    SetPasswordRequest,
    SetupTokenRequest,
    SetupTokenResponse,
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


def _set_auth_cookie(response: Response, token: str) -> None:
    """Attach the JWT as an httpOnly cookie.

    - httponly: JS can't read it (XSS can't steal the token).
    - samesite=strict: not sent on cross-site requests (CSRF mitigation).
    - secure: only over HTTPS in AWS; omitted locally so http://localhost works.
    - max_age matches the token TTL so the cookie expires with the JWT.
    """
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=IS_AWS,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", samesite="strict", secure=IS_AWS)


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
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
    token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "tv": user.token_version or 0}
    )
    _set_auth_cookie(response, token)
    # The JWT is delivered ONLY via the httpOnly cookie (no token in the body) —
    # the SPA uses the cookie + /api/auth/me. Not returning the raw token avoids
    # re-exposing it to JS / response logs.
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Clear the auth cookie AND revoke outstanding tokens for this user.

    Best-effort revocation: if the request carries a valid token we bump the
    user's token_version so any other copy of that token (incl. a leaked one)
    stops working immediately. The cookie is always cleared regardless.
    """
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        try:
            from auth import decode_token

            payload = decode_token(token)
            uid = payload.get("sub")
            if uid is not None:
                user = db.query(User).filter(User.id == int(uid)).first()
                if user is not None:
                    user.token_version = (user.token_version or 0) + 1
                    db.commit()
        except Exception:
            pass  # never let revocation failure block logout
    _clear_auth_cookie(response)
    return {"ok": True}


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Self-service password change: verify the CURRENT password, set the new
    one, and revoke all outstanding tokens (bump token_version) so other
    sessions are logged out. Re-issues a fresh cookie for this session."""
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
    current_user.hashed_password = hash_password(req.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    current_user.must_change_password = 0
    db.commit()
    db.refresh(current_user)
    # Re-issue a cookie carrying the new token_version so THIS session stays in.
    token = create_access_token(
        {
            "sub": str(current_user.id),
            "role": current_user.role.value,
            "tv": current_user.token_version,
        }
    )
    _set_auth_cookie(response, token)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user so the SPA can get role/identity without
    reading the (now httpOnly) JWT client-side."""
    return current_user


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
