"""SQLAlchemy models for the life plan tracker."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Role(str, enum.Enum):
    admin = "admin"
    child = "child"
    readonly = "readonly"


class Pillar(str, enum.Enum):
    spiritual = "spiritual"
    financial = "financial"
    education = "education"
    character = "character"
    life_skills = "life_skills"
    heritage = "heritage"
    economy = "economy"
    resilience = "resilience"
    dimensional_navigation = "dimensional_navigation"


class BountyTier(str, enum.Enum):
    bronze = "bronze"
    silver = "silver"
    gold = "gold"
    platinum = "platinum"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(200), nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.readonly)
    created_at = Column(DateTime, default=datetime.utcnow)

    # A child user links to their profile
    profile = relationship("Profile", back_populates="user", uselist=False)
    # Admin/readonly users can be granted access to profiles
    profile_access = relationship("ProfileAccess", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(200), nullable=False)
    date_of_birth = Column(String(10), nullable=True)  # YYYY-MM-DD
    avatar = Column(String(500), nullable=True)  # cropped avatar filename in uploads/
    avatar_original = Column(String(500), nullable=True)  # original full photo filename
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")
    entries = relationship("PillarEntry", back_populates="profile")
    access_grants = relationship("ProfileAccess", back_populates="profile")
    behavior_scores = relationship("BehaviorScore", back_populates="profile")
    bounties = relationship("Bounty", back_populates="profile")
    wishlist = relationship("WishlistItem", back_populates="profile")


class ProfileAccess(Base):
    """Grants a user access to view/edit a profile."""

    __tablename__ = "profile_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)

    user = relationship("User", back_populates="profile_access")
    profile = relationship("Profile", back_populates="access_grants")


class PillarEntry(Base):
    """A tracked entry for a pillar at a point in time.
    
    Milestones can have children (sub-events, notes, evidence) via parent_id.
    Status codes for milestones:
      - not_started: Seeded but not yet relevant
      - introduced: Concept introduced to child
      - in_progress: Actively working on it
      - practicing: Demonstrated but not consistent
      - complete: Consistently demonstrated / achieved
      - mastered: Fully internalized, can teach others
    For non-milestone entries (notes/events): status is always 'complete'.
    """

    __tablename__ = "pillar_entries"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("pillar_entries.id"), nullable=True)  # sub-entries nest under milestones
    pillar = Column(Enum(Pillar), nullable=False)
    entry_type = Column(String(20), default="milestone")  # milestone, event, note, evidence
    age_band = Column(String(10), nullable=True)  # e.g. "0-5", "6-12"
    age_years = Column(Integer, nullable=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # Foundation, Exploration, etc.
    score = Column(Integer, nullable=True)  # 1-5 optional rating
    is_milestone = Column(Integer, default=0)  # 1=framework goal, 0=user entry
    status = Column(String(20), default="not_started")  # not_started, introduced, in_progress, practicing, complete, mastered
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="entries")
    attachments = relationship("EventAttachment", back_populates="entry", cascade="all, delete-orphan")
    children = relationship("PillarEntry", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("PillarEntry", back_populates="children", remote_side=[id])


class BehaviorScore(Base):
    """Weekly character/behavior scores that gate bounty eligibility."""

    __tablename__ = "behavior_scores"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    week_of = Column(String(10), nullable=False)  # YYYY-MM-DD (Monday of that week)
    integrity = Column(Integer, default=3)  # 1-5
    honesty = Column(Integer, default=3)
    responsibility = Column(Integer, default=3)
    respect = Column(Integer, default=3)
    school_effort = Column(Integer, default=3)
    citizenship = Column(Integer, default=3)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="behavior_scores")


class Bounty(Base):
    """A bounty task that can be claimed and completed for reward."""

    __tablename__ = "bounties"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    tier = Column(Enum(BountyTier), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    reward_amount = Column(Integer, default=0)  # cents
    status = Column(String(20), default="available")  # available, claimed, complete, paid
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="bounties")


class WishlistItem(Base):
    """A child's wishlist item they're saving toward."""

    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    cost_cents = Column(Integer, default=0)
    url = Column(String(500), nullable=True)
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high
    status = Column(String(20), default="saving")  # saving, approved, purchased
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="wishlist")


class EventAttachment(Base):
    """File attachment (image, video, document) linked to a pillar entry event."""

    __tablename__ = "event_attachments"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("pillar_entries.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_name = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    entry = relationship("PillarEntry", back_populates="attachments")
