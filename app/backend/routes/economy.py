"""Behavior scoring and bounty routes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import BehaviorIncident, BehaviorScore, Bounty, User, WishlistItem
from schemas import (
    BehaviorScoreCreate, BehaviorScoreResponse, BehaviorScoreUpdate,
    BountyCreate, BountyResponse, BountyUpdate,
    IncidentCreate, IncidentResponse,
    WishlistCreate, WishlistResponse, WishlistUpdate,
)

router = APIRouter(prefix="/api/profiles/{profile_id}", tags=["economy"])

TRAITS = ["integrity", "honesty", "responsibility", "respect", "school_effort", "citizenship"]

# --- Behavior Incidents ---

@router.get("/incidents", response_model=list[IncidentResponse])
def list_incidents(profile_id: int, days: int = 30, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    return db.query(BehaviorIncident).filter(
        BehaviorIncident.profile_id == profile_id,
        BehaviorIncident.date >= cutoff,
    ).order_by(BehaviorIncident.date.desc()).all()


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(profile_id: int, req: IncidentCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    if req.trait not in TRAITS:
        raise HTTPException(status_code=400, detail=f"Trait must be one of: {TRAITS}")
    incident = BehaviorIncident(profile_id=profile_id, **req.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.delete("/incidents/{incident_id}", status_code=204)
def delete_incident(profile_id: int, incident_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    inc = db.query(BehaviorIncident).filter(BehaviorIncident.id == incident_id, BehaviorIncident.profile_id == profile_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    db.delete(inc)
    db.commit()


# --- Behavior Scores (legacy — kept for backward compat) ---

@router.get("/behavior", response_model=list[BehaviorScoreResponse])
def list_behavior(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(BehaviorScore).filter(BehaviorScore.profile_id == profile_id).order_by(BehaviorScore.week_of.desc()).all()


@router.post("/behavior", response_model=BehaviorScoreResponse, status_code=201)
def create_behavior(profile_id: int, req: BehaviorScoreCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    score = BehaviorScore(profile_id=profile_id, **req.model_dump())
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.patch("/behavior/{score_id}", response_model=BehaviorScoreResponse)
def update_behavior(profile_id: int, score_id: int, req: BehaviorScoreUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    score = db.query(BehaviorScore).filter(BehaviorScore.id == score_id, BehaviorScore.profile_id == profile_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(score, field, value)
    db.commit()
    db.refresh(score)
    return score


# --- Bounties ---

def _compute_current_reward(bounty):
    """Calculate the current reward after decay. Resets if reset_days have passed."""
    if not bounty.repeatable or bounty.times_completed == 0:
        return bounty.reward_amount
    times = bounty.times_completed
    # Check if reset period has elapsed
    if bounty.reset_days and bounty.last_completed_at:
        from datetime import timedelta
        if datetime.utcnow() - bounty.last_completed_at >= timedelta(days=bounty.reset_days):
            return bounty.reward_amount  # reset
    divisor = bounty.decay_divisor or 2
    return max(1, bounty.reward_amount // (divisor ** times))


def _compute_streak_bonus(bounty):
    """Calculate streak bonus. 4=2x, 12=5x, 52=20x base reward."""
    streak = bounty.streak_count or 0
    if streak >= 52:
        return bounty.reward_amount * 20
    if streak >= 12:
        return bounty.reward_amount * 5
    if streak >= 4:
        return bounty.reward_amount * 2
    return 0


def _bounty_response(bounty):
    """Convert a Bounty ORM object to a response dict with current_reward."""
    import json
    return {
        "id": bounty.id,
        "profile_id": bounty.profile_id,
        "pillar": bounty.pillar,
        "tier": bounty.tier,
        "title": bounty.title,
        "description": bounty.description,
        "requirements": bounty.requirements,
        "reference": bounty.reference,
        "criteria": bounty.criteria,
        "reward_amount": bounty.reward_amount,
        "age_band": bounty.age_band,
        "category": bounty.category,
        "repeatable": bounty.repeatable,
        "decay_divisor": bounty.decay_divisor or 2,
        "reset_days": bounty.reset_days,
        "times_completed": bounty.times_completed or 0,
        "streak_count": bounty.streak_count or 0,
        "streak_best": bounty.streak_best or 0,
        "streak_bonus": _compute_streak_bonus(bounty),
        "last_completed_at": bounty.last_completed_at,
        "current_reward": _compute_current_reward(bounty),
        "prerequisites": json.loads(bounty.prerequisites) if bounty.prerequisites else [],
        "status": bounty.status,
        "completed_at": bounty.completed_at,
        "created_at": bounty.created_at,
    }


@router.get("/bounties", response_model=list[BountyResponse])
def list_bounties(profile_id: int, pillar: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = db.query(Bounty).filter(Bounty.profile_id == profile_id)
    if pillar:
        q = q.filter(Bounty.pillar == pillar)
    bounties = q.order_by(Bounty.reward_amount.desc()).all()
    # Check for reset on repeatable bounties
    for b in bounties:
        if b.repeatable and b.reset_days and b.last_completed_at and b.times_completed:
            from datetime import timedelta
            elapsed = datetime.utcnow() - b.last_completed_at
            if elapsed >= timedelta(days=b.reset_days):
                b.times_completed = 0
                b.streak_count = 0  # streak broken
                b.last_completed_at = None
                if b.status == 'paid':
                    b.status = 'available'
    db.commit()
    return [_bounty_response(b) for b in bounties]


@router.post("/bounties", response_model=BountyResponse, status_code=201)
def create_bounty(profile_id: int, req: BountyCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    bounty = Bounty(profile_id=profile_id, **req.model_dump())
    db.add(bounty)
    db.commit()
    db.refresh(bounty)
    return _bounty_response(bounty)


@router.patch("/bounties/{bounty_id}", response_model=BountyResponse)
def update_bounty(profile_id: int, bounty_id: int, req: BountyUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    import json
    bounty = db.query(Bounty).filter(Bounty.id == bounty_id, Bounty.profile_id == profile_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    # Check prerequisites before allowing claim/advance (skip for admin resets)
    if req.status in ("claimed", "complete", "paid") and bounty.prerequisites:
        prereq_ids = json.loads(bounty.prerequisites)
        if prereq_ids:
            unmet = db.query(Bounty).filter(Bounty.id.in_(prereq_ids), Bounty.profile_id == profile_id).filter(
                ~((Bounty.status == "paid") | ((Bounty.repeatable == 1) & (Bounty.times_completed > 0)))
            ).all()
            if unmet:
                names = [b.title for b in unmet]
                raise HTTPException(status_code=400, detail=f"Prerequisites not met: {', '.join(names)}")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(bounty, field, value)
    if req.status == "paid" and bounty.repeatable:
        # Repeatable: increment times_completed, update streak, reset to available
        bounty.times_completed = (bounty.times_completed or 0) + 1
        bounty.streak_count = (bounty.streak_count or 0) + 1
        if bounty.streak_count > (bounty.streak_best or 0):
            bounty.streak_best = bounty.streak_count
        bounty.last_completed_at = datetime.utcnow()
        bounty.status = "available"
        bounty.completed_at = None
    elif req.status == "paid" and not bounty.repeatable and bounty.category:
        # Program completion bounty: close out all bounties in this category
        bounty.completed_at = datetime.utcnow()
        siblings = db.query(Bounty).filter(
            Bounty.profile_id == profile_id,
            Bounty.category == bounty.category,
            Bounty.id != bounty.id,
        ).all()
        for sib in siblings:
            sib.status = "retired"
    elif req.status in ("available", "claimed", "complete") and bounty.category and not bounty.repeatable:
        # If un-completing a program completion bounty, un-retire siblings
        siblings = db.query(Bounty).filter(
            Bounty.profile_id == profile_id,
            Bounty.category == bounty.category,
            Bounty.id != bounty.id,
            Bounty.status == "retired",
        ).all()
        for sib in siblings:
            sib.status = "available"
    elif req.status == "complete":
        bounty.completed_at = datetime.utcnow()
    # Allow manual reset of decay via times_completed = 0
    if hasattr(req, 'times_completed') and req.times_completed is not None:
        pass  # already set via setattr loop above
    db.commit()
    db.refresh(bounty)
    return _bounty_response(bounty)


@router.delete("/bounties/{bounty_id}", status_code=204)
def delete_bounty(profile_id: int, bounty_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    bounty = db.query(Bounty).filter(Bounty.id == bounty_id, Bounty.profile_id == profile_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    db.delete(bounty)
    db.commit()


# --- Bounty Logs ---

from pydantic import BaseModel as _BM

class _BountyLogCreate(_BM):
    author: str = "parent"
    entry_type: str = "note"  # note, submission, feedback, evidence
    content: str


@router.get("/bounties/{bounty_id}/logs")
def list_bounty_logs(profile_id: int, bounty_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from models import BountyLog
    return db.query(BountyLog).filter(BountyLog.bounty_id == bounty_id).order_by(BountyLog.created_at.asc()).all()


@router.post("/bounties/{bounty_id}/logs", status_code=201)
def create_bounty_log(profile_id: int, bounty_id: int, req: _BountyLogCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    from models import BountyLog
    bounty = db.query(Bounty).filter(Bounty.id == bounty_id, Bounty.profile_id == profile_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    log = BountyLog(bounty_id=bounty_id, author=req.author, entry_type=req.entry_type, content=req.content)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/bounties/{bounty_id}/logs/{log_id}", status_code=204)
def delete_bounty_log(profile_id: int, bounty_id: int, log_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    from models import BountyLog
    log = db.query(BountyLog).filter(BountyLog.id == log_id, BountyLog.bounty_id == bounty_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    db.delete(log)
    db.commit()


@router.get("/research-topics")
def get_research_topics(profile_id: int, _: User = Depends(get_current_user)):
    """Return the topic banks for research bounties."""
    from research_topics import RESEARCH_TOPICS
    return RESEARCH_TOPICS


@router.get("/programs")
def get_programs(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Return program definitions with progress for this profile."""
    from programs import PROGRAMS

    all_bounties = db.query(Bounty).filter(Bounty.profile_id == profile_id, Bounty.category != None).all()

    result = []
    for prog in PROGRAMS:
        # Match bounties by category
        prog_bounties = [b for b in all_bounties if b.category in prog["categories"]]
        # For marriage_prep, also filter by title keywords
        if "filter_titles" in prog:
            prog_bounties = [b for b in all_bounties if b.category in prog["categories"] and any(ft in b.title for ft in prog["filter_titles"])]
            if not prog_bounties:
                prog_bounties = [b for b in all_bounties if b.category in prog["categories"]]

        TIER_SORT = ['bronze','silver','gold','platinum','diamond','obsidian','legendary','covenant','ooh_shiny','ironforged']
        prog_bounties.sort(key=lambda b: (TIER_SORT.index(b.tier.value if hasattr(b.tier, 'value') else b.tier) if (b.tier.value if hasattr(b.tier, 'value') else b.tier) in TIER_SORT else 99, -b.reward_amount))

        from program_phases import PROGRAM_PHASES
        phases = PROGRAM_PHASES.get(prog["key"], {})

        total = len(prog_bounties)
        completed = sum(1 for b in prog_bounties if b.status == 'paid' or (b.repeatable and (b.times_completed or 0) > 0))
        one_time_reward = sum(b.reward_amount for b in prog_bounties if not b.repeatable)
        repeatable_base = sum(b.reward_amount for b in prog_bounties if b.repeatable)
        total_reward = one_time_reward + repeatable_base
        # If pick-one-pathway, show max single bounty reward, not sum
        if prog.get("max_one_pathway") and prog_bounties:
            total_reward = max(b.reward_amount for b in prog_bounties)
            repeatable_base = 0
        result.append({
            "key": prog["key"],
            "title": prog["title"],
            "icon": prog["icon"],
            "description": prog["description"],
            "total": total,
            "completed": completed,
            "total_reward": total_reward,
            "has_repeatable": repeatable_base > 0,
            "phases": phases,
            "bounties": [_bounty_response(b) for b in prog_bounties],
        })
    return result


# --- Eligibility Check ---

@router.get("/eligibility")
def check_eligibility(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Check bounty tier eligibility based on behavior incidents (last 30 days).
    
    Scoring: For each trait, ratio = positives / (positives + negatives).
    Overall average of all trait ratios determines tier.
    
    >=90% → Platinum | >=70% → Gold | >=50% → Silver | <50% → Bronze
    """
    cutoff = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    incidents = db.query(BehaviorIncident).filter(
        BehaviorIncident.profile_id == profile_id,
        BehaviorIncident.date >= cutoff,
    ).all()

    if not incidents:
        # No incidents recorded — start at Bronze, must earn higher tiers
        return {
            "eligible_tier": "bronze",
            "percentage": 0,
            "trait_scores": {t: {"positive": 0, "negative": 0, "ratio": 0} for t in TRAITS},
            "message": "No incidents recorded — start at Bronze, earn your way up",
        }

    # Calculate per-trait ratios
    trait_scores = {}
    for trait in TRAITS:
        trait_incidents = [i for i in incidents if i.trait == trait]
        if not trait_incidents:
            trait_scores[trait] = {"positive": 0, "negative": 0, "ratio": 0}  # no incidents = unproven
            continue
        pos = sum(1 for i in trait_incidents if i.positive)
        neg = sum(1 for i in trait_incidents if not i.positive)
        ratio = round((pos / (pos + neg)) * 100) if (pos + neg) > 0 else 100
        trait_scores[trait] = {"positive": pos, "negative": neg, "ratio": ratio}

    overall = round(sum(t["ratio"] for t in trait_scores.values()) / len(TRAITS))

    if overall >= 90:
        tier = "platinum"
    elif overall >= 70:
        tier = "gold"
    elif overall >= 50:
        tier = "silver"
    else:
        tier = "bronze"

    return {"eligible_tier": tier, "percentage": overall, "trait_scores": trait_scores}


# --- Earnings Summary ---

@router.get("/earnings")
def earnings_summary(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Summary of earned money from completed bounties."""
    bounties = db.query(Bounty).filter(Bounty.profile_id == profile_id).all()
    completed = [b for b in bounties if b.status in ("complete", "paid")]
    total_cents = sum(b.reward_amount for b in completed)
    paid = sum(b.reward_amount for b in bounties if b.status == "paid")
    unpaid = total_cents - paid

    return {
        "total_earned_cents": total_cents,
        "total_earned": f"${total_cents / 100:.2f}",
        "paid_out": f"${paid / 100:.2f}",
        "pending_payout": f"${unpaid / 100:.2f}",
        "bounties_completed": len(completed),
        "bounties_available": len([b for b in bounties if b.status == "available"]),
    }


# --- Wishlist ---

@router.get("/wishlist", response_model=list[WishlistResponse])
def list_wishlist(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(WishlistItem).filter(WishlistItem.profile_id == profile_id).order_by(WishlistItem.priority.desc(), WishlistItem.created_at).all()


@router.post("/wishlist", response_model=WishlistResponse, status_code=201)
def create_wishlist_item(profile_id: int, req: WishlistCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    item = WishlistItem(profile_id=profile_id, **req.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/wishlist/{item_id}", response_model=WishlistResponse)
def update_wishlist_item(profile_id: int, item_id: int, req: WishlistUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    item = db.query(WishlistItem).filter(WishlistItem.id == item_id, WishlistItem.profile_id == profile_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/wishlist/{item_id}", status_code=204)
def delete_wishlist_item(profile_id: int, item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    item = db.query(WishlistItem).filter(WishlistItem.id == item_id, WishlistItem.profile_id == profile_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
