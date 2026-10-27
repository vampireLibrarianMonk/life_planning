"""Event routes - create entries with file attachments."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child, require_profile_access
from database import get_db
from models import EventAttachment, PillarEntry, Profile, ProfileAccess, Role, User
from schemas import AttachmentResponse
from storage import get_storage

ALLOWED_MIME_PREFIXES = (
    "image/",
    "video/",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats",
    "text/",
)

router = APIRouter(
    prefix="/api/profiles/{profile_id}/entries/{entry_id}/attachments",
    tags=["events"],
    dependencies=[Depends(require_profile_access)],
)


@router.post("/", response_model=list[AttachmentResponse], status_code=201)
async def upload_attachments(
    profile_id: int,
    entry_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    entry = (
        db.query(PillarEntry)
        .filter(PillarEntry.id == entry_id, PillarEntry.profile_id == profile_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # DoS guards: cap the number of files per request and each file's size.
    MAX_FILES = 20
    MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB per file
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Too many files (max {MAX_FILES}).")

    results = []
    for f in files:
        # content_type is attacker-supplied and may be None — validate defensively.
        if not f.content_type or not any(
            f.content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES
        ):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.content_type}")
        ext = Path(f.filename or "").suffix
        stored_name = f"{uuid.uuid4().hex}{ext}"
        content = await f.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB).",
            )
        get_storage().save(stored_name, content, f.content_type)
        att = EventAttachment(
            entry_id=entry_id,
            filename=stored_name,
            original_name=f.filename,
            mime_type=f.content_type,
            size_bytes=len(content),
        )
        db.add(att)
        results.append(att)
    db.commit()
    for a in results:
        db.refresh(a)
    return results


@router.get("/", response_model=list[AttachmentResponse])
def list_attachments(
    profile_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entry = (
        db.query(PillarEntry)
        .filter(PillarEntry.id == entry_id, PillarEntry.profile_id == profile_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return db.query(EventAttachment).filter(EventAttachment.entry_id == entry_id).all()


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(
    profile_id: int,
    entry_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    att = (
        db.query(EventAttachment)
        .filter(EventAttachment.id == attachment_id, EventAttachment.entry_id == entry_id)
        .first()
    )
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    get_storage().delete(att.filename)
    db.delete(att)
    db.commit()


# Serve uploaded files
file_router = APIRouter(prefix="/api/uploads", tags=["events"])


def _profile_id_for_upload(db: Session, filename: str) -> int | None:
    """Resolve a stored upload key back to the profile that owns it.

    A key is either an EventAttachment.filename (join entry -> profile) or a
    Profile.avatar / avatar_original. Returns None if the key is unknown.
    """
    att = (
        db.query(PillarEntry.profile_id)
        .join(EventAttachment, EventAttachment.entry_id == PillarEntry.id)
        .filter(EventAttachment.filename == filename)
        .first()
    )
    if att:
        return att[0]
    prof = (
        db.query(Profile.id)
        .filter((Profile.avatar == filename) | (Profile.avatar_original == filename))
        .first()
    )
    return prof[0] if prof else None


@file_router.get("/{filename}")
def serve_upload(
    filename: str,
    request: Request,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Serve an attachment, AUTHORIZED to the owning profile.

    The JWT is taken from the httpOnly auth cookie (preferred — <img>/<video>/<a>
    tags send cookies automatically) or, as a fallback, a `?token=` query param.
    It resolves the file's owning profile and applies the same access rule as
    the rest of that profile's data (admin / readonly / owning child / granted).
    Unknown keys, bad tokens, and keys the caller can't access all return 404
    (no existence oracle).

    Local mode: stream the file from disk (as an attachment, benign type).
    AWS mode: redirect to a short-lived presigned S3 URL (minted ONLY after the
    access check passes).
    """
    from jose import JWTError

    import auth as _auth

    not_found = HTTPException(status_code=404, detail="Not found")

    # Reject path-escape attempts outright (keys are server-generated uuids).
    if "/" in filename or "\\" in filename or ".." in filename:
        raise not_found

    # Cookie-first, then the query-param token fallback.
    jwt_token = request.cookies.get(_auth.AUTH_COOKIE_NAME) or token
    if not jwt_token:
        raise not_found
    try:
        payload = _auth.decode_token(jwt_token)
        sub = payload.get("sub")
        if sub is None:
            raise not_found
        current_user = db.query(User).filter(User.id == int(sub)).first()
    except (JWTError, TypeError, ValueError):
        raise not_found
    if current_user is None:
        raise not_found

    profile_id = _profile_id_for_upload(db, filename)
    if profile_id is None:
        raise not_found

    # Enforce the same per-profile access as all other profile data.
    if current_user.role in (Role.admin, Role.readonly):
        pass
    elif current_user.role == Role.child:
        if not (current_user.profile and current_user.profile.id == profile_id):
            raise not_found
    else:
        granted = (
            db.query(ProfileAccess)
            .filter(
                ProfileAccess.user_id == current_user.id,
                ProfileAccess.profile_id == profile_id,
            )
            .first()
        )
        if not granted:
            raise not_found

    storage = get_storage()
    local_path = storage.open_local(filename)
    if local_path is not None:
        # Force download disposition + benign type so a malicious upload can't
        # execute in the app origin (e.g. HTML/SVG). nosniff is also set globally.
        return FileResponse(
            local_path,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment", "X-Content-Type-Options": "nosniff"},
        )
    # Non-local backend (S3): redirect to a presigned URL (post-authz only).
    return RedirectResponse(url=storage.url_for(filename), status_code=307)
