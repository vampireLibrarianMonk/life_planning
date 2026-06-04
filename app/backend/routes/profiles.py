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
                status="pending",
            )
            db.add(entry)

    db.commit()
    db.refresh(profile)
    return profile


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
