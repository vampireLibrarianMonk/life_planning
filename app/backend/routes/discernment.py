"""Discernment journal routes — reflective entries on fundamental domains."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import DiscernmentJournal, User

router = APIRouter(prefix="/api/profiles/{profile_id}/discernment", tags=["discernment"])

CATEGORIES = ["health", "math", "science", "civics", "relationships", "faith", "tradition", "law", "network", "calling"]

CATEGORY_META = {
    "health": {"icon": "🫀", "title": "Health", "question": "What is my body doing and what does it need?"},
    "math": {"icon": "📐", "title": "Math", "question": "What mathematical patterns govern the decisions I'm making?"},
    "science": {"icon": "🔬", "title": "Science", "question": "How do I know what I think I know?"},
    "civics": {"icon": "🏛️", "title": "Civics", "question": "What systems am I participating in?"},
    "relationships": {"icon": "🤝", "title": "Relationships", "question": "Who am I becoming because of the people around me?"},
    "faith": {"icon": "🕯️", "title": "Faith", "question": "What do I believe about what I cannot see?"},
    "tradition": {"icon": "⚓", "title": "Tradition", "question": "What was built before me, why was it built, and what breaks if I tear it down?"},
    "law": {"icon": "⚖️", "title": "Law", "question": "What rules bind me, who made them, and what is the difference between legal and just?"},
    "network": {"icon": "🕸️", "title": "Network", "question": "What holds this group together, what happens if I dissent, and can I survive alone if I must?"},
    "calling": {"icon": "📣", "title": "Calling", "question": "What is pulling me toward this path, who benefits from my decision, and what does the full picture look like?"},
}


class JournalCreate(BaseModel):
    category: str
    title: str
    reflection: str
    age_at_entry: int | None = None


class JournalUpdate(BaseModel):
    title: str | None = None
    reflection: str | None = None


class JournalResponse(BaseModel):
    id: int
    profile_id: int
    category: str
    title: str
    reflection: str
    age_at_entry: int | None
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}


@router.get("/categories")
def get_categories(profile_id: int, _: User = Depends(get_current_user)):
    """Return discernment categories with metadata."""
    return CATEGORY_META


@router.get("/")
def list_entries(profile_id: int, category: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """List discernment journal entries, optionally filtered by category."""
    q = db.query(DiscernmentJournal).filter(DiscernmentJournal.profile_id == profile_id)
    if category:
        q = q.filter(DiscernmentJournal.category == category)
    return q.order_by(DiscernmentJournal.created_at.desc()).all()


@router.post("/", status_code=201)
def create_entry(profile_id: int, req: JournalCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Create a new discernment journal entry."""
    if req.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {CATEGORIES}")
    entry = DiscernmentJournal(profile_id=profile_id, **req.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}")
def update_entry(profile_id: int, entry_id: int, req: JournalUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Update a discernment journal entry."""
    entry = db.query(DiscernmentJournal).filter(DiscernmentJournal.id == entry_id, DiscernmentJournal.profile_id == profile_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_entry(profile_id: int, entry_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Delete a discernment journal entry."""
    entry = db.query(DiscernmentJournal).filter(DiscernmentJournal.id == entry_id, DiscernmentJournal.profile_id == profile_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
