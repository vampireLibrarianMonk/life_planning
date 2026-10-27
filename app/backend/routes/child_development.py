"""Child Development section routes.

A top-level dashboard section (same level as Life Maps), NOT a pillar. Objectives
are stored as PillarEntry rows tagged category='child_development:<domain>'
(family-readable); the parent's private "worries" note is stored as
category='child_development_private' and served ONLY to admin + the owning child.

Per-objective CRUD (edit/mark/delete, add custom objective) and accomplishment
photo uploads reuse the existing /entries and attachment routes. This router
adds the CD-specific pieces: list (grouped), seed/deactivate an age group, and
the private worries note.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import (
    require_admin_or_child,
    require_private_profile_access,
    require_profile_access,
)
from child_development import (
    AGE_GROUP_LABELS,
    AGE_GROUPS,
    CD_PILLAR,
    CD_PRIVATE_CATEGORY,
    DOMAINS,
    OBJECTIVES,
    category_for,
)
from database import get_db
from models import PillarEntry, User

router = APIRouter(
    prefix="/api/profiles/{profile_id}/child-development",
    tags=["child_development"],
    dependencies=[Depends(require_profile_access)],
)


def _cd_objective_rows(db: Session, profile_id: int):
    """All Child Development objective rows (family-readable) for a profile."""
    prefix = "child_development:"
    return (
        db.query(PillarEntry)
        .filter(
            PillarEntry.profile_id == profile_id,
            PillarEntry.category.like(prefix + "%"),
        )
        .all()
    )


@router.get("/")
def overview(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_profile_access),
):
    """Which age groups are active (have objective rows) + the full catalog of
    available groups, sorted by age. Family-readable."""
    rows = _cd_objective_rows(db, profile_id)
    active = sorted({r.age_band for r in rows}, key=lambda b: AGE_GROUPS.get(b, 9999))
    catalog = [
        {
            "age_band": b,
            "label": AGE_GROUP_LABELS[b],
            "months": AGE_GROUPS[b],
            "active": b in active,
        }
        for b in sorted(AGE_GROUPS, key=lambda b: AGE_GROUPS[b])
    ]
    return {"active": active, "catalog": catalog, "domains": DOMAINS}


@router.get("/{age_band}")
def age_group(
    profile_id: int,
    age_band: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_profile_access),
):
    """Objectives for one age group, grouped by domain. Family-readable."""
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    rows = [r for r in _cd_objective_rows(db, profile_id) if r.age_band == age_band]
    by_domain: dict[str, list] = {k: [] for k in DOMAINS}
    for r in rows:
        # category is 'child_development:<domain_key>'
        domain_key = (r.category or "").split(":", 1)[-1]
        if domain_key in by_domain:
            by_domain[domain_key].append(
                {
                    "id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "content": r.content,
                    "age_band": r.age_band,
                }
            )
    return {
        "age_band": age_band,
        "label": AGE_GROUP_LABELS[age_band],
        "domains": DOMAINS,
        "objectives": by_domain,
    }


@router.post("/{age_band}/seed", status_code=201)
def seed_age_group(
    profile_id: int,
    age_band: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Activate an age group by seeding its objective rows. Idempotent — skips
    objectives that already exist for this profile/age group."""
    if age_band not in OBJECTIVES:
        raise HTTPException(status_code=404, detail="Unknown age group")
    existing = {
        (r.category, r.title) for r in _cd_objective_rows(db, profile_id) if r.age_band == age_band
    }
    created = 0
    for domain_key, items in OBJECTIVES[age_band].items():
        cat = category_for(domain_key)
        for title in items:
            if (cat, title) in existing:
                continue
            db.add(
                PillarEntry(
                    profile_id=profile_id,
                    pillar=CD_PILLAR,
                    entry_type="milestone",
                    is_milestone=1,
                    status="not_started",
                    age_band=age_band,
                    age_years=AGE_GROUPS[age_band],
                    category=cat,
                    title=title,
                )
            )
            created += 1
    db.commit()
    return {"age_band": age_band, "created": created, "already_present": len(existing)}


@router.delete("/{age_band}", status_code=204)
def deactivate_age_group(
    profile_id: int,
    age_band: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Deactivate an age group: delete its objective rows (cascade removes any
    sub-entries / attachments)."""
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    rows = [r for r in _cd_objective_rows(db, profile_id) if r.age_band == age_band]
    for r in rows:
        db.delete(r)
    db.commit()


# --- Private "questions & worries" note (admin + owning child ONLY) ----------


class WorriesUpdate(BaseModel):
    content: str


@router.get("/{age_band}/worries")
def get_worries(
    profile_id: int,
    age_band: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_private_profile_access),
):
    """The private parent/child-only 'questions & worries' note for an age group.
    Readonly family is blocked (require_private_profile_access)."""
    row = (
        db.query(PillarEntry)
        .filter(
            PillarEntry.profile_id == profile_id,
            PillarEntry.category == CD_PRIVATE_CATEGORY,
            PillarEntry.age_band == age_band,
        )
        .first()
    )
    return {"age_band": age_band, "content": row.content if row else ""}


@router.put("/{age_band}/worries")
def set_worries(
    profile_id: int,
    age_band: str,
    req: WorriesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_private_profile_access),
):
    """Create/update the private worries note. Write requires admin or the
    owning child (readonly blocked by the guard)."""
    if current_user.role.value not in ("admin", "child"):
        raise HTTPException(status_code=403, detail="Not permitted")
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    row = (
        db.query(PillarEntry)
        .filter(
            PillarEntry.profile_id == profile_id,
            PillarEntry.category == CD_PRIVATE_CATEGORY,
            PillarEntry.age_band == age_band,
        )
        .first()
    )
    if row:
        row.content = req.content
    else:
        row = PillarEntry(
            profile_id=profile_id,
            pillar=CD_PILLAR,
            entry_type="note",
            is_milestone=0,
            status="complete",
            age_band=age_band,
            age_years=AGE_GROUPS[age_band],
            category=CD_PRIVATE_CATEGORY,
            title="Questions & worries for the next check-up",
            content=req.content,
        )
        db.add(row)
    db.commit()
    return {"age_band": age_band, "content": row.content}
