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

import re

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
from models import MediaObjectiveLink, PillarEntry, User

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


def _domain_label(domain_key: str) -> str:
    """Human label for a domain: the built-in name, or a humanized slug for
    parent-created domains ('my_checks' -> 'My Checks')."""
    if domain_key in DOMAINS:
        return DOMAINS[domain_key]
    return domain_key.replace("_", " ").strip().title() or domain_key


def _slugify_domain(name: str) -> str:
    """Slugify a parent-provided domain name into a stable category suffix."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "custom"


@router.get("/{age_band}")
def age_group(
    profile_id: int,
    age_band: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_profile_access),
):
    """Objectives for one age group, grouped by domain. Family-readable.
    Parent-created (custom) domains are included after the built-in ones."""
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    rows = [r for r in _cd_objective_rows(db, profile_id) if r.age_band == age_band]
    by_domain: dict[str, list] = {k: [] for k in DOMAINS}
    for r in rows:
        # category is 'child_development:<domain_key>'
        domain_key = (r.category or "").split(":", 1)[-1]
        by_domain.setdefault(domain_key, []).append(
            {
                "id": r.id,
                "title": r.title,
                "status": r.status,
                "content": r.content,
                "age_band": r.age_band,
            }
        )
    # Ordered: built-in domains that have rows (catalog order), then custom
    # ones. A built-in key that was renamed away or emptied by the parent
    # disappears from the view; the checklist sync re-adds its items if wanted.
    domains: dict[str, str] = {}
    for k in DOMAINS:
        if by_domain.get(k):
            domains[k] = _domain_label(k)
    for k, items in by_domain.items():
        if items and k not in domains:
            domains[k] = _domain_label(k)
    return {
        "age_band": age_band,
        "label": AGE_GROUP_LABELS[age_band],
        "domains": domains,
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
        # Drop any gallery links to this objective FIRST (SQLite FK cascade is
        # not enforced), but NEVER the canonical media itself.
        db.query(MediaObjectiveLink).filter(MediaObjectiveLink.objective_id == r.id).delete(
            synchronize_session=False
        )
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


# --- Domain (category) CRUD: built-in and parent-created domains --------------


class DomainCreate(BaseModel):
    name: str
    first_item: str | None = None


class DomainRename(BaseModel):
    name: str


def _rows_for_domain(db: Session, profile_id: int, age_band: str, domain_key: str):
    cat = category_for(domain_key)
    return [
        r
        for r in _cd_objective_rows(db, profile_id)
        if r.age_band == age_band and r.category == cat
    ]


def _drop_rows(db: Session, rows) -> None:
    for r in rows:
        # Drop gallery links first (SQLite FK cascade is not enforced), but
        # NEVER the canonical media itself.
        db.query(MediaObjectiveLink).filter(MediaObjectiveLink.objective_id == r.id).delete(
            synchronize_session=False
        )
        db.delete(r)


@router.post("/{age_band}/domains", status_code=201)
def create_domain(
    profile_id: int,
    age_band: str,
    req: DomainCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Create a parent-defined domain for this age group, optionally with its
    first objective. The domain lives in the category suffix, so it is
    per-profile and is never touched by the built-in checklist sync."""
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="Domain name is required")
    domain_key = _slugify_domain(req.name)
    cat = category_for(domain_key)
    existing = [r for r in _cd_objective_rows(db, profile_id) if r.age_band == age_band]
    if any(r.category == cat for r in existing) and not req.first_item:
        raise HTTPException(status_code=409, detail="That domain already exists for this age group")
    row = PillarEntry(
        profile_id=profile_id,
        pillar=CD_PILLAR,
        entry_type="milestone",
        is_milestone=1,
        status="not_started",
        age_band=age_band,
        age_years=AGE_GROUPS[age_band],
        category=cat,
        title=(req.first_item or req.name.strip())[:300],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "age_band": age_band,
        "domain_key": domain_key,
        "label": _domain_label(domain_key),
        "first_item_id": row.id,
    }


@router.patch("/{age_band}/domains/{domain_key}")
def rename_domain(
    profile_id: int,
    age_band: str,
    domain_key: str,
    req: DomainRename,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Rename a domain (built-in or parent-created) for this age group: the
    category suffix is rewritten on every row in it. Note: re-running the
    built-in checklist sync re-adds built-in domains under their original key."""
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="Domain name is required")
    new_key = _slugify_domain(req.name)
    old_cat = category_for(domain_key)
    rows = [
        r
        for r in _cd_objective_rows(db, profile_id)
        if r.age_band == age_band and r.category == old_cat
    ]
    if not rows:
        raise HTTPException(status_code=404, detail="Domain not found for this age group")
    new_cat = category_for(new_key)
    if new_key != domain_key and any(
        r.category == new_cat for r in _cd_objective_rows(db, profile_id) if r.age_band == age_band
    ):
        raise HTTPException(
            status_code=409, detail="A domain with that name already exists for this age group"
        )
    for r in rows:
        r.category = new_cat
    db.commit()
    return {
        "age_band": age_band,
        "domain_key": new_key,
        "label": _domain_label(new_key),
        "renamed": len(rows),
    }


@router.delete("/{age_band}/domains/{domain_key}", status_code=204)
def delete_domain(
    profile_id: int,
    age_band: str,
    domain_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Delete a domain and every objective in it (gallery links are removed;
    the canonical media itself is kept)."""
    if age_band not in AGE_GROUPS:
        raise HTTPException(status_code=404, detail="Unknown age group")
    rows = _rows_for_domain(db, profile_id, age_band, domain_key)
    if not rows:
        raise HTTPException(status_code=404, detail="Domain not found for this age group")
    _drop_rows(db, rows)
    db.commit()
