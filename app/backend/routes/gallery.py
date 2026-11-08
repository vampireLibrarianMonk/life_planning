"""Gallery routes — the canonical, child-scoped media store.

Design (per v6 handoff, Pass 1):
  * ONE private gallery per child (ProfileMedia), independent of objectives.
  * Deactivating an age group / deleting an objective removes only the
    MediaObjectiveLink, never the underlying media.
  * Every route is scoped by profile_id via require_profile_access (router-level)
    plus require_admin_or_child for writes, so readonly users can view but not
    mutate, and a child cannot touch another child's profile.
  * Reuses the existing storage abstraction (local disk / presigned S3) — no new
    AWS dependency for local work.
"""

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import require_admin_or_child, require_profile_access
from database import get_db
from models import MediaObjectiveLink, PillarEntry, ProfileMedia, User
from schemas import MediaResponse, MediaUpdate, ObjectiveLinkCreate
from storage import get_storage

ALLOWED_MIME_PREFIXES = (
    "image/",
    "video/",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats",
    "text/",
)
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB per file (matches events.py; direct-S3 comes in Pass 3)

router = APIRouter(
    prefix="/api/profiles/{profile_id}/gallery",
    tags=["gallery"],
    dependencies=[Depends(require_profile_access)],
)


def _media_type_for(mime: str) -> str:
    if mime.startswith("image/"):
        return "photo"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith(("application/", "text/")):
        return "document"
    return "other"


def _serialize(media: ProfileMedia) -> MediaResponse:
    resp = MediaResponse.model_validate(media)
    resp.url = get_storage().url_for(media.storage_key)
    resp.objective_ids = [link.objective_id for link in media.objective_links]
    return resp


def _get_media_or_404(db: Session, profile_id: int, media_id: int) -> ProfileMedia:
    media = (
        db.query(ProfileMedia)
        .filter(
            ProfileMedia.id == media_id,
            ProfileMedia.profile_id == profile_id,  # cross-profile guard
            ProfileMedia.deleted_at.is_(None),
        )
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


@router.get("/", response_model=list[MediaResponse])
def list_gallery(
    profile_id: int,
    age_band: str | None = None,
    media_type: str | None = None,
    objective_id: int | None = None,
    db: Session = Depends(get_db),
):
    """List this child's media, newest first, with optional filters."""
    q = db.query(ProfileMedia).filter(
        ProfileMedia.profile_id == profile_id,
        ProfileMedia.deleted_at.is_(None),
    )
    if age_band:
        q = q.filter(ProfileMedia.age_band == age_band)
    if media_type:
        q = q.filter(ProfileMedia.media_type == media_type)
    if objective_id is not None:
        q = q.join(MediaObjectiveLink, MediaObjectiveLink.media_id == ProfileMedia.id).filter(
            MediaObjectiveLink.objective_id == objective_id
        )
    items = q.order_by(ProfileMedia.created_at.desc(), ProfileMedia.id.desc()).all()
    return [_serialize(m) for m in items]


@router.post("/", response_model=list[MediaResponse], status_code=201)
async def upload_media(
    profile_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_child),
):
    """Upload one or more files straight into the canonical gallery.

    (Pass 1 uses the existing buffered-upload path, same 25 MB cap as events.
    Pass 3 replaces large-video uploads with direct-to-S3 + finalize.)
    """
    MAX_FILES = 20
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Too many files (max {MAX_FILES}).")

    created: list[ProfileMedia] = []
    for f in files:
        # content_type is attacker-supplied and may be None — validate defensively.
        if not f.content_type or not any(
            f.content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES
        ):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.content_type}")
        content = await f.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB).",
            )
        stored_name = f"{uuid.uuid4().hex}_{f.filename}"
        get_storage().save(stored_name, content, f.content_type)
        media = ProfileMedia(
            profile_id=profile_id,
            owner_id=current_user.id,
            storage_key=stored_name,
            original_name=f.filename or stored_name,
            mime_type=f.content_type,
            media_type=_media_type_for(f.content_type),
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            status="ready",
        )
        db.add(media)
        created.append(media)
    db.commit()
    for m in created:
        db.refresh(m)
    return [_serialize(m) for m in created]


@router.get("/{media_id}", response_model=MediaResponse)
def get_media(profile_id: int, media_id: int, db: Session = Depends(get_db)):
    return _serialize(_get_media_or_404(db, profile_id, media_id))


@router.patch("/{media_id}", response_model=MediaResponse)
def update_media(
    profile_id: int,
    media_id: int,
    req: MediaUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    media = _get_media_or_404(db, profile_id, media_id)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(media, field, value)
    db.commit()
    db.refresh(media)
    return _serialize(media)


@router.delete("/{media_id}", status_code=204)
def delete_media(
    profile_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Soft-delete a gallery item. The stored object is removed too."""
    media = _get_media_or_404(db, profile_id, media_id)
    from datetime import datetime

    media.deleted_at = datetime.utcnow()
    db.commit()
    # Remove the stored bytes; metadata row is retained (soft delete) for audit.
    try:
        get_storage().delete(media.storage_key)
    except Exception:  # noqa: BLE001 - best-effort; the row is already tombstoned
        pass


@router.post("/{media_id}/objective-links", response_model=MediaResponse, status_code=201)
def link_objective(
    profile_id: int,
    media_id: int,
    req: ObjectiveLinkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Associate a gallery item with an objective (same-profile only)."""
    media = _get_media_or_404(db, profile_id, media_id)
    objective = (
        db.query(PillarEntry)
        .filter(PillarEntry.id == req.objective_id, PillarEntry.profile_id == profile_id)
        .first()
    )
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found on this profile")
    exists = (
        db.query(MediaObjectiveLink)
        .filter(
            MediaObjectiveLink.media_id == media_id,
            MediaObjectiveLink.objective_id == req.objective_id,
        )
        .first()
    )
    if not exists:
        db.add(
            MediaObjectiveLink(
                profile_id=profile_id, media_id=media_id, objective_id=req.objective_id
            )
        )
        db.commit()
    db.refresh(media)
    return _serialize(media)


@router.delete("/{media_id}/objective-links/{objective_id}", status_code=204)
def unlink_objective(
    profile_id: int,
    media_id: int,
    objective_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Remove an objective association. The media itself is untouched."""
    _get_media_or_404(db, profile_id, media_id)  # ensures same-profile
    link = (
        db.query(MediaObjectiveLink)
        .filter(
            MediaObjectiveLink.media_id == media_id,
            MediaObjectiveLink.objective_id == objective_id,
            MediaObjectiveLink.profile_id == profile_id,
        )
        .first()
    )
    if link:
        db.delete(link)
        db.commit()
