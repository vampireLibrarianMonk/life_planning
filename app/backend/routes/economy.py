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


def _bounty_response(bounty):
    """Convert a Bounty ORM object to a response dict with current_reward."""
    return {
        "id": bounty.id,
        "profile_id": bounty.profile_id,
        "pillar": bounty.pillar,
        "tier": bounty.tier,
        "title": bounty.title,
        "description": bounty.description,
        "reward_amount": bounty.reward_amount,
        "age_band": bounty.age_band,
        "repeatable": bounty.repeatable,
        "decay_divisor": bounty.decay_divisor or 2,
        "reset_days": bounty.reset_days,
        "times_completed": bounty.times_completed or 0,
        "last_completed_at": bounty.last_completed_at,
        "current_reward": _compute_current_reward(bounty),
        "status": bounty.status,
        "completed_at": bounty.completed_at,
        "created_at": bounty.created_at,
    }


@router.get("/bounties", response_model=list[BountyResponse])
def list_bounties(profile_id: int, pillar: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = db.query(Bounty).filter(Bounty.profile_id == profile_id)
    if pillar:
        q = q.filter(Bounty.pillar == pillar)
    bounties = q.order_by(Bounty.created_at.desc()).all()
    # Check for reset on repeatable bounties
    for b in bounties:
        if b.repeatable and b.reset_days and b.last_completed_at and b.times_completed:
            from datetime import timedelta
            if datetime.utcnow() - b.last_completed_at >= timedelta(days=b.reset_days):
                b.times_completed = 0
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
    bounty = db.query(Bounty).filter(Bounty.id == bounty_id, Bounty.profile_id == profile_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(bounty, field, value)
    if req.status == "paid" and bounty.repeatable:
        # Repeatable: increment times_completed, reset to available
        bounty.times_completed = (bounty.times_completed or 0) + 1
        bounty.last_completed_at = datetime.utcnow()
        bounty.status = "available"
        bounty.completed_at = None
    elif req.status == "complete":
        bounty.completed_at = datetime.utcnow()
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
