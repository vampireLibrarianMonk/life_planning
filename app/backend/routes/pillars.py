"""Pillar tracking entry routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import PillarEntry, User
from schemas import PillarEntryCreate, PillarEntryResponse, PillarEntryUpdate, Pillar

router = APIRouter(prefix="/api/profiles/{profile_id}/entries", tags=["pillars"])


@router.get("/", response_model=list[PillarEntryResponse])
def list_entries(
    profile_id: int,
    pillar: Pillar | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(PillarEntry).filter(PillarEntry.profile_id == profile_id)
    if pillar:
        q = q.filter(PillarEntry.pillar == pillar)
    return q.order_by(PillarEntry.is_milestone.desc(), PillarEntry.age_band, PillarEntry.created_at).all()


@router.post("/", response_model=PillarEntryResponse, status_code=201)
def create_entry(
    profile_id: int,
    req: PillarEntryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    data = req.model_dump()
    is_milestone = data.pop("is_milestone", 0)
    entry = PillarEntry(profile_id=profile_id, is_milestone=is_milestone, status="pending" if is_milestone else "complete", **data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=PillarEntryResponse)
def update_entry(
    profile_id: int,
    entry_id: int,
    req: PillarEntryUpdate,
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
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    profile_id: int,
    entry_id: int,
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
    db.delete(entry)
    db.commit()
