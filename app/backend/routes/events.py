"""Event routes - create entries with file attachments."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import EventAttachment, PillarEntry, User
from schemas import AttachmentResponse

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_MIME_PREFIXES = ("image/", "video/", "application/pdf", "application/msword",
                         "application/vnd.openxmlformats", "text/")

router = APIRouter(prefix="/api/profiles/{profile_id}/entries/{entry_id}/attachments", tags=["events"])


@router.post("/", response_model=list[AttachmentResponse], status_code=201)
async def upload_attachments(
    profile_id: int,
    entry_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    entry = db.query(PillarEntry).filter(
        PillarEntry.id == entry_id, PillarEntry.profile_id == profile_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    results = []
    for f in files:
        if not any(f.content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.content_type}")
        ext = Path(f.filename).suffix
        stored_name = f"{uuid.uuid4().hex}{ext}"
        dest = UPLOAD_DIR / stored_name
        content = await f.read()
        dest.write_bytes(content)
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
    entry = db.query(PillarEntry).filter(
        PillarEntry.id == entry_id, PillarEntry.profile_id == profile_id
    ).first()
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
    att = db.query(EventAttachment).filter(
        EventAttachment.id == attachment_id, EventAttachment.entry_id == entry_id
    ).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path = UPLOAD_DIR / att.filename
    if file_path.exists():
        file_path.unlink()
    db.delete(att)
    db.commit()


# Serve uploaded files
file_router = APIRouter(prefix="/api/uploads", tags=["events"])


@file_router.get("/{filename}")
def serve_upload(filename: str, _: User = Depends(get_current_user)):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
