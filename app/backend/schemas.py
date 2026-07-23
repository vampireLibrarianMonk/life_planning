"""Pydantic schemas for request/response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    admin = "admin"
    child = "child"
    readonly = "readonly"


class Pillar(str, Enum):
    spiritual = "spiritual"
    financial = "financial"
    education = "education"
    character = "character"
    life_skills = "life_skills"
    heritage = "heritage"
    economy = "economy"
    resilience = "resilience"
    dimensional_navigation = "dimensional_navigation"
    civic = "civic"
    scientific_reality_testing = "scientific_reality_testing"
    inheritance_burden_stewardship = "inheritance_burden_stewardship"
    catholic_formation = "catholic_formation"
    secular_sacred_formation = "secular_sacred_formation"


# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# Users
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: Role = Role.readonly


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: Role
    created_at: datetime

    model_config = {"from_attributes": True}


# Profiles
class ProfileCreate(BaseModel):
    name: str
    date_of_birth: str | None = None
    user_id: int | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    date_of_birth: str | None
    avatar: str | None
    avatar_original: str | None
    weekly_budget_cents: int | None = None
    monthly_budget_cents: int | None = None
    annual_budget_cents: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Pillar Entries
class PillarEntryCreate(BaseModel):
    pillar: Pillar
    parent_id: int | None = None
    entry_type: str = "milestone"  # milestone, event, note, evidence
    age_band: str | None = None
    age_years: int | None = None
    title: str
    content: str | None = None
    category: str | None = None
    score: int | None = None
    is_milestone: int = 0


class PillarEntryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    score: int | None = None
    age_years: int | None = None
    status: str | None = None


class PillarEntryResponse(BaseModel):
    id: int
    profile_id: int
    parent_id: int | None
    pillar: Pillar
    entry_type: str
    age_band: str | None
    age_years: int | None
    title: str
    content: str | None
    category: str | None
    score: int | None
    is_milestone: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Access
class ProfileAccessCreate(BaseModel):
    user_id: int
    profile_id: int


# Behavior Scores
class BehaviorScoreCreate(BaseModel):
    week_of: str
    integrity: int = 3
    honesty: int = 3
    responsibility: int = 3
    respect: int = 3
    school_effort: int = 3
    citizenship: int = 3
    notes: str | None = None


class BehaviorScoreUpdate(BaseModel):
    integrity: int | None = None
    honesty: int | None = None
    responsibility: int | None = None
    respect: int | None = None
    school_effort: int | None = None
    citizenship: int | None = None
    notes: str | None = None


class BehaviorScoreResponse(BaseModel):
    id: int
    profile_id: int
    week_of: str
    integrity: int
    honesty: int
    responsibility: int
    respect: int
    school_effort: int
    citizenship: int
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Bounties
class BountyTier(str, Enum):
    bronze = "bronze"
    silver = "silver"
    gold = "gold"
    platinum = "platinum"
    diamond = "diamond"
    obsidian = "obsidian"
    legendary = "legendary"
    covenant = "covenant"
    ooh_shiny = "ooh_shiny"
    ironforged = "ironforged"


class BountyCreate(BaseModel):
    tier: BountyTier
    title: str
    description: str | None = None
    requirements: str | None = None
    reference: str | None = None
    criteria: str | None = None
    reward_amount: int = 0  # cents
    pillar: Pillar | None = None
    age_band: str | None = None
    category: str | None = None
    repeatable: int = 0
    decay_divisor: int = 2
    reset_days: int | None = None


class BountyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    requirements: str | None = None
    reference: str | None = None
    criteria: str | None = None
    reward_amount: int | None = None
    status: str | None = None
    pillar: Pillar | None = None
    age_band: str | None = None
    category: str | None = None
    repeatable: int | None = None
    decay_divisor: int | None = None
    reset_days: int | None = None
    times_completed: int | None = None
    streak_count: int | None = None


class BountyResponse(BaseModel):
    id: int
    profile_id: int
    pillar: Pillar | None
    tier: BountyTier
    title: str
    description: str | None
    requirements: str | None
    reference: str | None
    criteria: str | None
    reward_amount: int
    age_band: str | None
    category: str | None
    repeatable: int
    decay_divisor: int
    reset_days: int | None
    times_completed: int
    streak_count: int
    streak_best: int
    streak_bonus: int  # computed: bonus earned at current streak milestone
    last_completed_at: datetime | None
    current_reward: int  # computed: what it's worth right now
    prerequisites: list[int]  # bounty IDs that must be paid first
    status: str
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Wishlist
class WishlistCreate(BaseModel):
    title: str
    description: str | None = None
    cost_cents: int = 0
    url: str | None = None
    priority: int = 1


class WishlistUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    cost_cents: int | None = None
    url: str | None = None
    priority: int | None = None
    status: str | None = None


class WishlistResponse(BaseModel):
    id: int
    profile_id: int
    title: str
    description: str | None
    cost_cents: int
    url: str | None
    priority: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# Event Attachments
class AttachmentResponse(BaseModel):
    id: int
    entry_id: int
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


# Behavior Incidents
class IncidentCreate(BaseModel):
    trait: str  # integrity, honesty, responsibility, respect, school_effort, citizenship
    positive: int = 1  # 1=positive, 0=negative
    description: str
    date: str  # YYYY-MM-DD


class IncidentResponse(BaseModel):
    id: int
    profile_id: int
    trait: str
    positive: int
    description: str
    date: str
    created_at: datetime

    model_config = {"from_attributes": True}
