"""Behavior scoring and bounty routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import BehaviorScore, Bounty, User, WishlistItem
from schemas import (
    BehaviorScoreCreate, BehaviorScoreResponse, BehaviorScoreUpdate,
    BountyCreate, BountyResponse, BountyUpdate,
    WishlistCreate, WishlistResponse, WishlistUpdate,
)

router = APIRouter(prefix="/api/profiles/{profile_id}", tags=["economy"])

# --- Behavior Scores ---

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

@router.get("/bounties", response_model=list[BountyResponse])
def list_bounties(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Bounty).filter(Bounty.profile_id == profile_id).order_by(Bounty.created_at.desc()).all()


@router.post("/bounties", response_model=BountyResponse, status_code=201)
def create_bounty(profile_id: int, req: BountyCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    bounty = Bounty(profile_id=profile_id, **req.model_dump())
    db.add(bounty)
    db.commit()
    db.refresh(bounty)
    return bounty


@router.patch("/bounties/{bounty_id}", response_model=BountyResponse)
def update_bounty(profile_id: int, bounty_id: int, req: BountyUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    bounty = db.query(Bounty).filter(Bounty.id == bounty_id, Bounty.profile_id == profile_id).first()
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(bounty, field, value)
    if req.status == "complete":
        bounty.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(bounty)
    return bounty


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
    """Check bounty tier eligibility based on latest behavior score."""
    latest = db.query(BehaviorScore).filter(BehaviorScore.profile_id == profile_id).order_by(BehaviorScore.week_of.desc()).first()
    if not latest:
        return {"eligible_tier": "bronze", "average": 0, "message": "No behavior scores yet — defaults to Bronze"}

    avg = (latest.integrity + latest.honesty + latest.responsibility + latest.respect + latest.school_effort + latest.citizenship) / 6

    if avg >= 4.5:
        tier = "platinum"
    elif avg >= 3.5:
        tier = "gold"
    elif avg >= 2.5:
        tier = "silver"
    else:
        tier = "bronze"

    return {"eligible_tier": tier, "average": round(avg, 1), "week_of": latest.week_of}


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
