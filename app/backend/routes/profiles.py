"""Profile CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin
from database import get_db
from models import PillarEntry, Profile, ProfileAccess, User
from schemas import ProfileAccessCreate, ProfileCreate, ProfileResponse
from seed_data import MILESTONES

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _get_accessible_profiles(user: User, db: Session) -> list[Profile]:
    if user.role.value == "admin":
        return db.query(Profile).all()
    if user.role.value == "child" and user.profile:
        return [user.profile]
    access_ids = [
        a.profile_id for a in db.query(ProfileAccess).filter(ProfileAccess.user_id == user.id).all()
    ]
    return db.query(Profile).filter(Profile.id.in_(access_ids)).all()


@router.get("/", response_model=list[ProfileResponse])
def list_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_accessible_profiles(current_user, db)


@router.post("/", response_model=ProfileResponse)
def create_profile(
    req: ProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    profile = Profile(name=req.name, date_of_birth=req.date_of_birth, user_id=req.user_id)
    db.add(profile)
    db.flush()

    # Seed milestones from the framework docs
    for pillar_key, milestones in MILESTONES.items():
        for m in milestones:
            entry = PillarEntry(
                profile_id=profile.id,
                pillar=pillar_key,
                age_band=m["age_band"],
                title=m["title"],
                category=m.get("category"),
                is_milestone=1,
                entry_type="milestone",
                status="not_started",
            )
            db.add(entry)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/{profile_id}/reseed", status_code=200)
def reseed_milestones(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Add any milestones from seed_data that don't already exist on this profile."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    existing = {
        (e.pillar.value if hasattr(e.pillar, 'value') else e.pillar, e.title)
        for e in db.query(PillarEntry).filter(
            PillarEntry.profile_id == profile_id, PillarEntry.is_milestone == 1
        ).all()
    }

    added = 0
    for pillar_key, milestones in MILESTONES.items():
        for m in milestones:
            if (pillar_key, m["title"]) not in existing:
                db.add(PillarEntry(
                    profile_id=profile_id,
                    pillar=pillar_key,
                    age_band=m["age_band"],
                    title=m["title"],
                    category=m.get("category"),
                    is_milestone=1,
                    entry_type="milestone",
                    status="not_started",
                ))
                added += 1

    db.commit()
    return {"detail": f"Added {added} new milestones", "added": added}


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible = _get_accessible_profiles(current_user, db)
    profile = next((p for p in accessible if p.id == profile_id), None)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/access", status_code=201)
def grant_access(
    req: ProfileAccessCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    access = ProfileAccess(user_id=req.user_id, profile_id=req.profile_id)
    db.add(access)
    db.commit()
    return {"detail": "Access granted"}
