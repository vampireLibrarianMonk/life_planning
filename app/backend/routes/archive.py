"""Archive / restore / delete for a profile.

Design (owner spec 2026-10-22):
  * ARCHIVE (admin + owning child): stream a .zip with a MODULAR subdir layout
    (per-domain JSON) plus the real upload files, so it's self-contained and
    restorable even if storage is wiped. Also returns a short-lived archive
    token (signed JWT) proving a backup was just taken.
  * DELETE (admin only): a FULL clean delete — every DB row AND every upload
    blob — but ONLY with a valid, fresh archive token (you must download a
    backup first).
  * RESTORE (admin only): a FULL restore that recreates the profile exactly as
    archived, preserving original IDs. Hard-fails if that profile id already
    exists (no overwrite, no messy id remapping).

The per-domain export map is the single place to extend as features grow — add
a domain entry and both archive and restore pick it up.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import auth
from auth import require_admin, require_private_profile_access
from database import get_db
from models import (
    BehaviorIncident,
    BehaviorScore,
    Bounty,
    BountyLog,
    Discernment,
    DiscernmentJournal,
    EventAttachment,
    Fund,
    FundTransaction,
    LessonPlan,
    LessonResponse,
    PillarEntry,
    Profile,
    User,
    WishlistItem,
)
from storage import get_storage

router = APIRouter(prefix="/api/profiles", tags=["archive"])

ARCHIVE_VERSION = 1
ARCHIVE_TOKEN_TTL_MIN = 10

# Per-domain export map: archive subpath -> (SQLAlchemy model, parent-join).
# Profile-owned tables filter on profile_id; grandchild tables join via parent.
# Order matters for restore (parents before children).
_PROFILE_TABLES = [
    ("pillars/entries.json", PillarEntry),
    ("economy/bounties.json", Bounty),
    ("economy/behavior.json", BehaviorScore),
    ("economy/incidents.json", BehaviorIncident),
    ("economy/wishlist.json", WishlistItem),
    ("funds/funds.json", Fund),
    ("discernment/journal.json", DiscernmentJournal),
    ("discernment/discernments.json", Discernment),
    ("lessons/lessons.json", LessonPlan),
]
# Grandchild tables: archive subpath -> (model, foreign-key attr, parent model).
_CHILD_TABLES = [
    ("economy/bounty_logs.json", BountyLog, "bounty_id", Bounty),
    ("funds/transactions.json", FundTransaction, "fund_id", Fund),
    ("lessons/responses.json", LessonResponse, "lesson_id", LessonPlan),
    ("pillars/attachments.json", EventAttachment, "entry_id", PillarEntry),
]


def _row_to_dict(row) -> dict:
    """Serialize an ORM row to JSON-safe primitives (enums -> value, dt -> iso)."""
    out = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif hasattr(val, "value"):  # enum
            val = val.value
        out[col.name] = val
    return out


def _mint_archive_token(profile_id: int, user_id: int) -> str:
    return jwt.encode(
        {
            "purpose": "archive",
            "profile_id": profile_id,
            "uid": user_id,  # bind to the user who took the backup
            "exp": datetime.now(UTC) + timedelta(minutes=ARCHIVE_TOKEN_TTL_MIN),
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )


def _verify_archive_token(token: str, profile_id: int, user_id: int) -> None:
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid or expired archive token.")
    if payload.get("purpose") != "archive" or payload.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Archive token does not match this profile.")
    # Bind to the acting user: a leaked token can't be used by a different
    # account (shrinks the replay/leak blast radius alongside the short TTL).
    if payload.get("uid") != user_id:
        raise HTTPException(status_code=403, detail="Archive token not valid for this user.")


@router.post("/{profile_id}/archive")
def archive_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_private_profile_access),
):
    """Stream a .zip backup of the whole profile (admin + owning child).

    The response carries an `X-Archive-Token` header; pass it back to DELETE to
    authorize a full clean delete.
    """
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    storage = get_storage()
    buf = io.BytesIO()
    counts: dict[str, int] = {}
    upload_keys: set[str] = set()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Profile record.
        zf.writestr("profile/profile.json", json.dumps(_row_to_dict(profile), indent=2))

        # Profile-owned tables.
        for path, model in _PROFILE_TABLES:
            rows = db.query(model).filter(model.profile_id == profile_id).all()
            zf.writestr(path, json.dumps([_row_to_dict(r) for r in rows], indent=2))
            counts[path] = len(rows)

        # Grandchild tables (joined through their parent to this profile).
        parent_ids = {
            Bounty: [r.id for r in db.query(Bounty).filter(Bounty.profile_id == profile_id)],
            Fund: [r.id for r in db.query(Fund).filter(Fund.profile_id == profile_id)],
            LessonPlan: [
                r.id for r in db.query(LessonPlan).filter(LessonPlan.profile_id == profile_id)
            ],
            PillarEntry: [
                r.id for r in db.query(PillarEntry).filter(PillarEntry.profile_id == profile_id)
            ],
        }
        for path, model, fk, parent_model in _CHILD_TABLES:
            ids = parent_ids[parent_model]
            rows = db.query(model).filter(getattr(model, fk).in_(ids)).all() if ids else []
            zf.writestr(path, json.dumps([_row_to_dict(r) for r in rows], indent=2))
            counts[path] = len(rows)
            if model is EventAttachment:
                upload_keys.update(r.filename for r in rows if r.filename)

        # Avatar(s).
        for key in (profile.avatar, profile.avatar_original):
            if key:
                upload_keys.add(key)

        # Real upload files.
        stored = 0
        for key in sorted(upload_keys):
            data = storage.read(key)
            if data is not None:
                zf.writestr(f"uploads/{key}", data)
                stored += 1

        manifest = {
            "archive_version": ARCHIVE_VERSION,
            "profile_id": profile_id,
            "profile_name": profile.name,
            "exported_at": datetime.now(UTC).isoformat(),
            "row_counts": counts,
            "upload_files": stored,
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    buf.seek(0)
    token = _mint_archive_token(profile_id, current_user.id)
    filename = f"life-plan-profile-{profile_id}-archive.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Archive-Token": token,
            "Access-Control-Expose-Headers": "X-Archive-Token",
        },
    )


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: int,
    archive_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """FULL clean delete (admin only) — requires a fresh archive token.

    Removes every DB row for the profile AND every upload blob. The caller must
    first POST /archive and pass the returned token here (query param
    `archive_token`), proving a backup was taken. The token is bound to the
    acting admin and short-lived.
    """
    _verify_archive_token(archive_token, profile_id, current_user.id)

    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    storage = get_storage()

    # Collect upload keys to delete from storage (attachments + avatars).
    entry_ids = [r.id for r in db.query(PillarEntry).filter(PillarEntry.profile_id == profile_id)]
    blob_keys: set[str] = set()
    if entry_ids:
        for att in db.query(EventAttachment).filter(EventAttachment.entry_id.in_(entry_ids)):
            if att.filename:
                blob_keys.add(att.filename)
    for key in (profile.avatar, profile.avatar_original):
        if key:
            blob_keys.add(key)

    # Delete DB rows (ORM cascade handles grandchildren).
    for lesson in db.query(LessonPlan).filter(LessonPlan.profile_id == profile_id):
        db.delete(lesson)
    for fund in db.query(Fund).filter(Fund.profile_id == profile_id):
        db.delete(fund)
    for bounty in db.query(Bounty).filter(Bounty.profile_id == profile_id):
        db.delete(bounty)
    all_entries = db.query(PillarEntry).filter(PillarEntry.profile_id == profile_id).all()
    for e in [x for x in all_entries if x.parent_id is not None]:
        db.delete(e)
    db.flush()
    for e in [x for x in all_entries if x.parent_id is None]:
        db.delete(e)
    for model in (BehaviorScore, BehaviorIncident, WishlistItem, Discernment, DiscernmentJournal):
        for row in db.query(model).filter(model.profile_id == profile_id):
            db.delete(row)
    db.delete(profile)
    db.commit()

    # Delete blobs AFTER the DB commit (so a storage hiccup can't orphan rows).
    for key in blob_keys:
        try:
            storage.delete(key)
        except Exception:  # noqa: BLE001 — best-effort blob cleanup
            pass

    return {"deleted": True, "profile_id": profile_id, "blobs_removed": len(blob_keys)}


@router.post("/restore", status_code=201)
async def restore_profile(
    file: UploadFile,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """FULL restore (admin only) from an archive .zip — original IDs preserved.

    Hard-fails if a profile with the archived id already exists (no overwrite).
    """
    raw = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Not a valid archive .zip")

    def _load(path: str):
        try:
            return json.loads(zf.read(path))
        except KeyError:
            return [] if path != "profile/profile.json" else None

    manifest = _load("manifest.json") or {}
    if manifest.get("archive_version") != ARCHIVE_VERSION:
        raise HTTPException(status_code=400, detail="Unsupported archive version")

    profile_data = _load("profile/profile.json")
    if not profile_data:
        raise HTTPException(status_code=400, detail="Archive missing profile record")

    pid = profile_data["id"]
    if db.query(Profile).filter(Profile.id == pid).first():
        raise HTTPException(
            status_code=409,
            detail=f"Profile id {pid} already exists — delete it before restoring.",
        )

    storage = get_storage()

    # Restore upload blobs first (so attachment rows point at live files).
    # Hardening: reject keys that try to escape the storage root (path traversal
    # in local mode) and never overwrite an existing blob (a crafted archive must
    # not be able to clobber another profile's live files). A cumulative
    # decompressed-size cap defends against a zip bomb.
    MAX_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024  # 500 MB across all blobs
    MAX_RATIO = 200  # per-entry compression-ratio sanity cap
    total_uncompressed = 0
    for info in zf.infolist():
        name = info.filename
        if not name.startswith("uploads/") or name.endswith("/"):
            continue
        # Reject absurd compression ratios (classic zip-bomb signature).
        if info.compress_size > 0 and info.file_size / info.compress_size > MAX_RATIO:
            raise HTTPException(status_code=400, detail="Archive entry failed ratio check")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise HTTPException(status_code=413, detail="Archive too large when decompressed")
        key = name[len("uploads/") :]
        if not key or "/" in key or "\\" in key or ".." in key:
            raise HTTPException(status_code=400, detail="Archive contains an invalid upload path")
        if storage.read(key) is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Refusing to overwrite an existing stored file: {key}",
            )
        storage.save(key, zf.read(name), "application/octet-stream")

    def _coerce(model, row: dict) -> dict:
        """Turn ISO datetime strings back into datetime objects for DateTime
        columns (archive stores them as ISO strings)."""
        from datetime import datetime as _dt

        from sqlalchemy import DateTime

        out = dict(row)
        for col in model.__table__.columns:
            if isinstance(col.type, DateTime) and isinstance(out.get(col.name), str):
                try:
                    out[col.name] = _dt.fromisoformat(out[col.name])
                except ValueError:
                    pass
        return out

    def _insert(model, rows):
        for r in rows:
            db.add(model(**_coerce(model, r)))
        db.flush()

    # Parents first, then grandchildren (FK order).
    db.add(Profile(**_coerce(Profile, profile_data)))
    db.flush()
    for path, model in _PROFILE_TABLES:
        _insert(model, _load(path))
    for path, model, _fk, _parent in _CHILD_TABLES:
        _insert(model, _load(path))

    db.commit()
    return {
        "restored": True,
        "profile_id": pid,
        "name": profile_data.get("name"),
    }
