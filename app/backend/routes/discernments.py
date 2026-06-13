"""Discernment & Formation routes."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import Discernment, User

router = APIRouter(prefix="/api/profiles/{profile_id}/discernments", tags=["discernments"])


class DiscernmentCreate(BaseModel):
    category: str
    title: str
    notes: str | None = None


class DiscernmentUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    notes: str | None = None


class DiscernmentResponse(BaseModel):
    id: int
    profile_id: int
    category: str
    title: str
    status: str
    notes: str | None
    started_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[DiscernmentResponse])
def list_discernments(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Discernment).filter(Discernment.profile_id == profile_id).order_by(Discernment.category, Discernment.started_at.desc()).all()


@router.post("/", response_model=DiscernmentResponse, status_code=201)
def create_discernment(profile_id: int, req: DiscernmentCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    d = Discernment(profile_id=profile_id, **req.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.patch("/{disc_id}", response_model=DiscernmentResponse)
def update_discernment(profile_id: int, disc_id: int, req: DiscernmentUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    d = db.query(Discernment).filter(Discernment.id == disc_id, Discernment.profile_id == profile_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(d, field, value)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/{disc_id}", status_code=204)
def delete_discernment(profile_id: int, disc_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    d = db.query(Discernment).filter(Discernment.id == disc_id, Discernment.profile_id == profile_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(d)
    db.commit()
