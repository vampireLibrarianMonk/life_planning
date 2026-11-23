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
import io
import math
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import config
from auth import require_admin_or_child, require_profile_access
from database import get_db
from models import MediaObjectiveLink, PillarEntry, ProfileMedia, User
from schemas import (
    MediaObjectiveLinkResponse,
    MediaResponse,
    MediaUpdate,
    ObjectiveLinkCreate,
    PrintEvidenceUpdate,
    UploadFinalizeRequest,
    UploadInitiateRequest,
    UploadInitiateResponse,
)
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
MULTIPART_PART_BYTES = 8 * 1024 * 1024

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
    resp.objective_links = [
        MediaObjectiveLinkResponse.model_validate(link) for link in media.objective_links
    ]
    return resp


def _reused(media: ProfileMedia) -> MediaResponse:
    """Serialize an existing canonical object for an upload dedupe response."""
    resp = _serialize(media)
    resp.reused = True
    return resp


def _multipart_dedupe_key(part_checksums: list[str]) -> str:
    """Return a deterministic, domain-separated content fingerprint.

    S3 validates each signed SHA-256 part checksum. Hashing those fixed-size
    checksums lets us identify the exact same byte stream before it crosses a
    slow phone connection, without buffering an entire video in the browser or
    App Runner. The prefix prevents accidental equivalence with the legacy raw
    SHA-256 values stored for buffered uploads.
    """
    digest = hashlib.sha256(b"life-plan-gallery-multipart-v1\0")
    for checksum in part_checksums:
        digest.update(checksum.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _ready_media_with_hash(db: Session, profile_id: int, content_hash: str) -> ProfileMedia | None:
    return (
        db.query(ProfileMedia)
        .filter(
            ProfileMedia.profile_id == profile_id,
            ProfileMedia.sha256 == content_hash,
            ProfileMedia.deleted_at.is_(None),
            ProfileMedia.status == "ready",
        )
        .first()
    )


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


def _preview_image(data: bytes) -> bytes:
    """Make a small, safe JPEG derivative for the printable evidence appendix."""
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((720, 540))
            if image.mode not in ("RGB", "L"):
                background = Image.new("RGB", image.size, "white")
                background.paste(
                    image, mask=image.getchannel("A") if "A" in image.getbands() else None
                )
                image = background
            elif image.mode == "L":
                image = image.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=82, optimize=True)
            return output.getvalue()
    except Exception as exc:  # malformed images must not turn into a 500 during printing
        raise HTTPException(status_code=409, detail="Could not prepare image preview") from exc


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
        # Only fully-uploaded media; pending/failed direct uploads stay hidden
        # until their finalize confirms the object is really in storage.
        ProfileMedia.status == "ready",
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

    responses: list[MediaResponse] = []
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
        content_hash = hashlib.sha256(content).hexdigest()
        existing = _ready_media_with_hash(db, profile_id, content_hash)
        if existing:
            responses.append(_reused(existing))
            continue
        stored_name = f"{uuid.uuid4().hex}_{f.filename}"
        media = ProfileMedia(
            profile_id=profile_id,
            owner_id=current_user.id,
            storage_key=stored_name,
            original_name=f.filename or stored_name,
            mime_type=f.content_type,
            media_type=_media_type_for(f.content_type),
            size_bytes=len(content),
            sha256=content_hash,
            dedupe_key=content_hash,
            status="pending",
        )
        db.add(media)
        try:
            # Reserve this exact byte sequence before writing it to storage.
            # The partial unique index makes simultaneous browser uploads safe.
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = _ready_media_with_hash(db, profile_id, content_hash)
            if existing:
                responses.append(_reused(existing))
                continue
            raise HTTPException(
                status_code=409,
                detail="An identical media upload is already in progress.",
            )
        try:
            get_storage().save(stored_name, content, f.content_type)
        except Exception:
            media.status = "failed"
            media.dedupe_key = None
            db.commit()
            raise
        media.status = "ready"
        db.commit()
        db.refresh(media)
        responses.append(_serialize(media))
    return responses


@router.get("/{media_id}", response_model=MediaResponse)
def get_media(profile_id: int, media_id: int, db: Session = Depends(get_db)):
    return _serialize(_get_media_or_404(db, profile_id, media_id))


# --- Direct-to-storage upload for large videos (initiate -> PUT -> finalize) --
# The bytes go straight to S3 (or the local direct-PUT endpoint) and never pass
# through the app request body, so large videos bypass the request-size cap.


@router.post("/uploads/initiate", response_model=UploadInitiateResponse, status_code=201)
def initiate_upload(
    profile_id: int,
    req: UploadInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_child),
):
    if not any(req.content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {req.content_type}")
    expected_parts = math.ceil(req.size_bytes / MULTIPART_PART_BYTES)
    if len(req.part_checksums) != expected_parts:
        raise HTTPException(
            status_code=400, detail="Upload checksum parts do not match the file size."
        )
    content_hash = _multipart_dedupe_key(req.part_checksums)
    existing = _ready_media_with_hash(db, profile_id, content_hash)
    if existing:
        return UploadInitiateResponse(
            media_id=existing.id,
            upload_url="",
            storage_key="",
            method="existing",
            reused=True,
        )
    storage_key = f"{uuid.uuid4().hex}_{req.filename}"
    media = ProfileMedia(
        profile_id=profile_id,
        owner_id=current_user.id,
        storage_key=storage_key,
        original_name=req.filename,
        mime_type=req.content_type,
        media_type=_media_type_for(req.content_type),
        size_bytes=req.size_bytes,  # declared; verified at finalize
        sha256=content_hash,
        dedupe_key=content_hash,
        status="pending",
    )
    db.add(media)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _ready_media_with_hash(db, profile_id, content_hash)
        if existing:
            return UploadInitiateResponse(
                media_id=existing.id,
                upload_url="",
                storage_key="",
                method="existing",
                reused=True,
            )
        raise HTTPException(status_code=409, detail="An identical upload is already in progress.")
    db.refresh(media)
    storage = get_storage()
    if config.IS_AWS:
        try:
            upload_id = storage.create_multipart_upload(storage_key, req.content_type)
        except Exception as exc:
            media.status = "failed"
            media.dedupe_key = None
            db.commit()
            raise HTTPException(status_code=502, detail="Could not prepare secure upload.") from exc
        media.multipart_upload_id = upload_id
        db.commit()
        return UploadInitiateResponse(
            media_id=media.id,
            upload_url="",
            storage_key=storage_key,
            method="multipart",
            part_size=MULTIPART_PART_BYTES,
            part_urls=[
                storage.presigned_part_url(storage_key, upload_id, n, req.part_checksums[n - 1])
                for n in range(1, expected_parts + 1)
            ],
        )
    upload_url = storage.presigned_put_url(storage_key, req.content_type)
    return UploadInitiateResponse(media_id=media.id, upload_url=upload_url, storage_key=storage_key)


@router.post("/uploads/{media_id}/finalize", response_model=MediaResponse)
def finalize_upload(
    profile_id: int,
    media_id: int,
    req: UploadFinalizeRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    media = (
        db.query(ProfileMedia)
        .filter(ProfileMedia.id == media_id, ProfileMedia.profile_id == profile_id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Upload not found")
    if media.status == "ready":
        return _serialize(media)
    if media.multipart_upload_id:
        if not req.parts:
            raise HTTPException(status_code=400, detail="Multipart upload parts are required.")
        expected = math.ceil(media.size_bytes / MULTIPART_PART_BYTES)
        numbers = [p.part_number for p in req.parts]
        if numbers != list(range(1, expected + 1)):
            raise HTTPException(
                status_code=400, detail="Multipart upload parts are incomplete or invalid."
            )
        try:
            get_storage().complete_multipart_upload(
                media.storage_key,
                media.multipart_upload_id,
                [
                    {
                        "PartNumber": p.part_number,
                        "ETag": p.etag,
                        "ChecksumSHA256": p.checksum_sha256,
                    }
                    for p in req.parts
                ],
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409, detail="Could not complete multipart upload."
            ) from exc
        media.multipart_upload_id = None
    # The object must actually be present *and match the initiated size* before
    # we mark it ready.  A forged finalize or a client that uploads a different
    # sized object must not create a ready gallery record.
    stored_size = get_storage().object_size(media.storage_key)
    if stored_size != media.size_bytes:
        media.status = "failed"
        media.dedupe_key = None
        db.commit()
        raise HTTPException(
            status_code=409, detail="Uploaded object is missing or has an unexpected size."
        )
    media.status = "ready"
    if req.observation is not None:
        media.observation = req.observation
    if req.age_band is not None:
        media.age_band = req.age_band
    db.commit()
    db.refresh(media)
    return _serialize(media)


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
    # A pending multipart session otherwise retains S3 parts until provider
    # cleanup. Abort it before tombstoning the application record.
    if media.multipart_upload_id:
        try:
            get_storage().abort_multipart_upload(media.storage_key, media.multipart_upload_id)
        except Exception:
            pass
        media.multipart_upload_id = None
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


@router.put(
    "/{media_id}/objective-links/{objective_id}/print-evidence", response_model=MediaResponse
)
def update_print_evidence(
    profile_id: int,
    media_id: int,
    objective_id: int,
    req: PrintEvidenceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Opt a Gallery/objective link into the bounded printable appendix.

    Limits live here rather than in the browser: an objective gets at most two
    photos and one video, and every featured video needs an explicitly chosen,
    same-profile photo cover.  This also prevents a forged request from
    referencing another child's media.
    """
    media = _get_media_or_404(db, profile_id, media_id)
    link = (
        db.query(MediaObjectiveLink)
        .filter(
            MediaObjectiveLink.profile_id == profile_id,
            MediaObjectiveLink.media_id == media_id,
            MediaObjectiveLink.objective_id == objective_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Media is not linked to this objective")

    if not req.featured_for_print:
        link.featured_for_print = False
        link.print_order = None
        link.cover_media_id = None
    else:
        if media.media_type not in ("photo", "video"):
            raise HTTPException(
                status_code=400, detail="Only photos and videos can be printed as evidence"
            )
        existing_count = (
            db.query(MediaObjectiveLink)
            .join(ProfileMedia, ProfileMedia.id == MediaObjectiveLink.media_id)
            .filter(
                MediaObjectiveLink.profile_id == profile_id,
                MediaObjectiveLink.objective_id == objective_id,
                MediaObjectiveLink.featured_for_print.is_(True),
                ProfileMedia.media_type == media.media_type,
                MediaObjectiveLink.id != link.id,
            )
            .count()
        )
        limit = 2 if media.media_type == "photo" else 1
        if existing_count >= limit:
            raise HTTPException(
                status_code=409,
                detail=f"An objective can include at most {limit} {media.media_type}{'s' if limit > 1 else ''} in print.",
            )

        cover_id = None
        if media.media_type == "video":
            if req.cover_media_id is None:
                raise HTTPException(
                    status_code=400, detail="Select a Gallery photo as this video's print cover"
                )
            cover = _get_media_or_404(db, profile_id, req.cover_media_id)
            if cover.media_type != "photo" or cover.status != "ready":
                raise HTTPException(
                    status_code=400, detail="Video cover must be a ready Gallery photo"
                )
            cover_id = cover.id
        link.featured_for_print = True
        link.cover_media_id = cover_id
        if req.print_order is not None:
            link.print_order = req.print_order
        elif link.print_order is None:
            last_order = (
                db.query(MediaObjectiveLink.print_order)
                .filter(
                    MediaObjectiveLink.profile_id == profile_id,
                    MediaObjectiveLink.objective_id == objective_id,
                    MediaObjectiveLink.featured_for_print.is_(True),
                )
                .order_by(MediaObjectiveLink.print_order.desc())
                .first()
            )
            link.print_order = (
                (last_order[0] + 1) if last_order and last_order[0] is not None else 0
            )

    db.commit()
    db.refresh(media)
    return _serialize(media)


@router.get("/{media_id}/print-preview")
def print_preview(
    profile_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_profile_access),
):
    """Authenticated, bounded image derivative used only by printable evidence.

    The route intentionally proxies and resizes private storage bytes.  The
    browser and generated PDF therefore never receive an S3 object URL or the
    original-size photo.
    """
    media = _get_media_or_404(db, profile_id, media_id)
    if media.media_type != "photo" or media.status != "ready":
        raise HTTPException(status_code=404, detail="Printable image not found")
    data = get_storage().read(media.storage_key)
    if not data:
        raise HTTPException(status_code=404, detail="Printable image is missing")
    return Response(
        content=_preview_image(data),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )


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
