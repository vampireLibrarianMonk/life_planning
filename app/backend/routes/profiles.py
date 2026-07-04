"""Profile CRUD routes."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin, require_admin_or_child
from database import get_db
from models import Bounty, BountyTier, Pillar, PillarEntry, Profile, ProfileAccess, User
from schemas import ProfileAccessCreate, ProfileCreate, ProfileResponse
from seed_data import BOUNTIES, MILESTONES

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _seed_bounties(db: Session, profile_id: int) -> int:
    """Add or refresh default seeded bounties for a profile without wiping progress."""
    existing = {
        (b.category, b.title): b
        for b in db.query(Bounty).filter(Bounty.profile_id == profile_id).all()
    }
    added = 0
    updated = 0
    refresh_fields = (
        "tier",
        "description",
        "requirements",
        "reference",
        "criteria",
        "reward_amount",
        "pillar",
        "age_band",
        "repeatable",
        "decay_divisor",
        "reset_days",
    )
    for bounty in BOUNTIES:
        key = (bounty.get("category"), bounty["title"])
        data = bounty.copy()
        if data.get("tier"):
            data["tier"] = BountyTier(data["tier"])
        if data.get("pillar"):
            data["pillar"] = Pillar(data["pillar"])
        existing_bounty = existing.get(key)
        if existing_bounty:
            changed = False
            for field in refresh_fields:
                if field in data and getattr(existing_bounty, field) != data[field]:
                    setattr(existing_bounty, field, data[field])
                    changed = True
            if changed:
                updated += 1
            continue
        db.add(Bounty(profile_id=profile_id, **data))
        existing[key] = data
        added += 1
    return {"added": added, "updated": updated}


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

    _seed_bounties(db, profile.id)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/{profile_id}/reseed", status_code=200)
def reseed_milestones(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Add any milestones from seed_data that don't already exist on this profile.
    Also corrects age_band values on existing milestones if the seed data has changed."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    existing_entries = db.query(PillarEntry).filter(
        PillarEntry.profile_id == profile_id, PillarEntry.is_milestone == 1
    ).all()
    existing = {
        (e.pillar.value if hasattr(e.pillar, 'value') else e.pillar, e.title): e
        for e in existing_entries
    }

    added = 0
    updated_bands = 0
    for pillar_key, milestones in MILESTONES.items():
        for m in milestones:
            key = (pillar_key, m["title"])
            if key not in existing:
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
            else:
                # Correct age_band if seed data has changed (e.g. 0-5 → 0-2/2-3/3-5)
                entry = existing[key]
                if entry.age_band != m["age_band"]:
                    entry.age_band = m["age_band"]
                    updated_bands += 1

    bounty_sync = _seed_bounties(db, profile_id)

    db.commit()
    return {
        "detail": f"Added {added} new milestones, corrected {updated_bands} age bands, added {bounty_sync['added']} new bounties, and refreshed {bounty_sync['updated']} existing bounties",
        "added": added,
        "updated_bands": updated_bands,
        "bounties_added": bounty_sync["added"],
        "bounties_updated": bounty_sync["updated"],
    }


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


@router.post("/{profile_id}/avatar", response_model=ProfileResponse)
async def upload_avatar(
    profile_id: int,
    original: UploadFile = File(...),
    cropped: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Save original (full photo for gallery)
    orig_ext = Path(original.filename).suffix
    orig_name = f"avatar_orig_{profile_id}_{uuid.uuid4().hex}{orig_ext}"
    orig_content = await original.read()
    (UPLOAD_DIR / orig_name).write_bytes(orig_content)

    # Save cropped version
    crop_ext = Path(cropped.filename).suffix or ".png"
    crop_name = f"avatar_{profile_id}_{uuid.uuid4().hex}{crop_ext}"
    crop_content = await cropped.read()
    (UPLOAD_DIR / crop_name).write_bytes(crop_content)

    # Remove old files if they exist
    if profile.avatar:
        old = UPLOAD_DIR / profile.avatar
        if old.exists():
            old.unlink()
    if profile.avatar_original:
        old = UPLOAD_DIR / profile.avatar_original
        if old.exists():
            old.unlink()

    profile.avatar = crop_name
    profile.avatar_original = orig_name
    db.commit()
    db.refresh(profile)
    return profile


# --- Database Backup ---

@router.post("/backup", status_code=200)
def backup_database(_: User = Depends(require_admin)):
    """Create a timestamped backup of the SQLite database."""
    import shutil
    from datetime import datetime

    db_path = Path(__file__).parent.parent / "life_plan.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    backup_dir = Path(__file__).parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"life_plan_{timestamp}.db"
    backup_path = backup_dir / backup_name

    shutil.copy2(db_path, backup_path)

    # Keep only the last 10 backups to prevent disk bloat
    backups = sorted(backup_dir.glob("life_plan_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old_backup in backups[10:]:
        old_backup.unlink()

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    return {
        "detail": f"Backup created: {backup_name} ({size_mb:.2f} MB)",
        "filename": backup_name,
        "kept": min(len(backups), 10),
    }
