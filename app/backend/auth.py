"""JWT authentication and role-based access control."""

from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import config
from database import get_db
from models import Role, User

SECRET_KEY = config.get_jwt_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours (short-lived; re-login as needed)

# httpOnly cookie that carries the JWT. Preferred over the Authorization header
# so the token is never readable by JS (XSS can't exfiltrate it). The header
# path is retained as a fallback for API clients and a safe rollout.
AUTH_COOKIE_NAME = "lp_auth"

# auto_error=False so a missing header isn't an instant 401 — we fall back to
# the cookie before deciding the request is unauthenticated.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def extract_token(
    request: Request,
    header_token: str | None = Depends(oauth2_scheme),
) -> str | None:
    """Return the JWT from the httpOnly cookie (preferred) or Bearer header.

    Cookie-first means the browser SPA stops needing the token in JS; the header
    fallback keeps API clients and the migration window working.
    """
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    return cookie_token or header_token


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str | None = Depends(extract_token), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_admin_or_child(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (Role.admin, Role.child):
        raise HTTPException(status_code=403, detail="Write access required")
    return current_user


def require_write_access(current_user: User = Depends(get_current_user)) -> User:
    """Block readonly users from any write operation."""
    if current_user.role == Role.readonly:
        raise HTTPException(
            status_code=403, detail="Read-only access — write operations are not permitted"
        )
    return current_user


def require_private_access(current_user: User = Depends(get_current_user)) -> User:
    """Gate SENSITIVE reads to admin + the child themselves (readonly excluded).

    Used for the behavior-incident log, private discernment journals, and
    aggregate financial totals. A child user is already scoped to their own
    profile, so this yields "the child sees their own private data, a parent/
    admin sees it, and family readonly viewers do not."
    """
    if current_user.role not in (Role.admin, Role.child):
        raise HTTPException(
            status_code=403,
            detail="This information is private to the child and parents.",
        )
    return current_user


def require_profile_access(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorize access to a specific profile's data.

    Closes the cross-profile hole: a CHILD may only touch THEIR OWN profile
    (not another child's). Admin and readonly keep household-wide access (the
    owner's single-family model); any other role falls back to explicit
    ProfileAccess grants. Apply to every /profiles/{profile_id}/... route.
    """
    if current_user.role == Role.admin or current_user.role == Role.readonly:
        return current_user
    if current_user.role == Role.child:
        if current_user.profile and current_user.profile.id == profile_id:
            return current_user
        raise HTTPException(status_code=403, detail="You can only access your own profile.")
    # Any other role: explicit per-profile grant required.
    from models import ProfileAccess

    granted = (
        db.query(ProfileAccess)
        .filter(ProfileAccess.user_id == current_user.id, ProfileAccess.profile_id == profile_id)
        .first()
    )
    if not granted:
        raise HTTPException(status_code=403, detail="No access to this profile.")
    return current_user


def require_private_profile_access(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Combine private-data gating (readonly excluded) with per-profile scoping.

    Used for the behavior log, private journals, and financial totals: the
    requester must be admin (any profile) or the child who OWNS this profile.
    Readonly and other children are rejected.
    """
    if current_user.role == Role.admin:
        return current_user
    if current_user.role == Role.child:
        if current_user.profile and current_user.profile.id == profile_id:
            return current_user
        raise HTTPException(status_code=403, detail="You can only access your own profile.")
    raise HTTPException(
        status_code=403,
        detail="This information is private to the child and parents.",
    )
