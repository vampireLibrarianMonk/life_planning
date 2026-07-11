"""Lesson Plan routes — transcript-based lessons with rebrief, expansion, and teachback."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin, require_admin_or_child
from database import get_db
from models import LessonPlan, LessonResponse, User

router = APIRouter(prefix="/api/profiles/{profile_id}/lessons", tags=["lessons"])


class LessonCreate(BaseModel):
    title: str
    source: str | None = None
    url: str | None = None
    transcript: str
    notes: str | None = None
    pillar: str | None = None
    age_band: str | None = None


class LessonUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    url: str | None = None
    notes: str | None = None
    pillar: str | None = None
    age_band: str | None = None
    status: str | None = None


class ResponseCreate(BaseModel):
    response_type: str  # rebrief, expansion, teachback
    content: str


class LessonResponse_(BaseModel):
    id: int
    lesson_id: int
    response_type: str
    content: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class LessonOut(BaseModel):
    id: int
    profile_id: int
    pillar: str | None
    title: str
    source: str | None
    url: str | None
    transcript: str
    notes: str | None
    age_band: str | None
    status: str
    created_at: datetime | None = None
    responses: list[LessonResponse_] = []
    model_config = {"from_attributes": True}


@router.get("/", response_model=list[LessonOut])
def list_lessons(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """List all lesson plans for a profile."""
    return db.query(LessonPlan).filter(LessonPlan.profile_id == profile_id).order_by(LessonPlan.created_at.desc()).all()


@router.post("/", response_model=LessonOut, status_code=201)
def create_lesson(profile_id: int, req: LessonCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Create a new lesson plan (admin assigns transcript for child to study)."""
    lesson = LessonPlan(profile_id=profile_id, **req.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/{lesson_id}", response_model=LessonOut)
def get_lesson(profile_id: int, lesson_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Get a single lesson plan with its responses."""
    lesson = db.query(LessonPlan).filter(LessonPlan.id == lesson_id, LessonPlan.profile_id == profile_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.patch("/{lesson_id}", response_model=LessonOut)
def update_lesson(profile_id: int, lesson_id: int, req: LessonUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Update lesson metadata or status."""
    lesson = db.query(LessonPlan).filter(LessonPlan.id == lesson_id, LessonPlan.profile_id == profile_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/{lesson_id}", status_code=204)
def delete_lesson(profile_id: int, lesson_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Delete a lesson plan and all its responses."""
    lesson = db.query(LessonPlan).filter(LessonPlan.id == lesson_id, LessonPlan.profile_id == profile_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    db.delete(lesson)
    db.commit()


# --- Responses (child submits rebrief, expansion, teachback) ---

@router.post("/{lesson_id}/responses", response_model=LessonResponse_, status_code=201)
def create_response(profile_id: int, lesson_id: int, req: ResponseCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Child submits a response to a lesson (rebrief, expansion, or teachback)."""
    lesson = db.query(LessonPlan).filter(LessonPlan.id == lesson_id, LessonPlan.profile_id == profile_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if req.response_type not in ("rebrief", "expansion", "teachback"):
        raise HTTPException(status_code=400, detail="response_type must be: rebrief, expansion, or teachback")
    resp = LessonResponse(lesson_id=lesson_id, **req.model_dump())
    db.add(resp)
    # Auto-advance lesson status
    if req.response_type == "rebrief" and lesson.status in ("assigned", "in_progress"):
        lesson.status = "rebrief_done"
    elif req.response_type == "expansion" and lesson.status == "rebrief_done":
        lesson.status = "expansion_done"
    elif req.response_type == "teachback" and lesson.status in ("expansion_done", "rebrief_done"):
        lesson.status = "teachback_done"
    db.commit()
    db.refresh(resp)
    return resp


@router.delete("/{lesson_id}/responses/{response_id}", status_code=204)
def delete_response(profile_id: int, lesson_id: int, response_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Delete a lesson response."""
    resp = db.query(LessonResponse).filter(
        LessonResponse.id == response_id, LessonResponse.lesson_id == lesson_id
    ).first()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
    db.delete(resp)
    db.commit()
