"""Pydantic schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


def _validate_http_url(v: str | None) -> str | None:
    """Reject non-http(s) URLs (defense-in-depth vs. javascript:/data: links).

    React already neutralizes javascript: hrefs and the CSP blocks inline script,
    so this is belt-and-suspenders + anti-phishing: a stored link must be an
    ordinary web URL. Empty/None is allowed (the field is optional).
    """
    if v is None or v.strip() == "":
        return v
    s = v.strip()
    if not (s.lower().startswith("http://") or s.lower().startswith("https://")):
        raise ValueError("url must start with http:// or https://")
    return s


# Reusable constrained-int aliases (money is in integer cents; never negative).
Cents = Annotated[int, Field(ge=0, le=1_000_000_000)]  # 0 .. $10,000,000
OptCents = Annotated[int, Field(ge=0, le=1_000_000_000)]
Count = Annotated[int, Field(ge=0, le=1_000_000)]
Divisor = Annotated[int, Field(ge=2, le=1000)]  # decay divides by >=2
Score1to5 = Annotated[int, Field(ge=1, le=5)]
Days = Annotated[int, Field(ge=1, le=36500)]


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


class SetupTokenRequest(BaseModel):
    email: str | None = None
    expires_hours: int = 24


class SetupTokenResponse(BaseModel):
    username: str
    role: Role
    setup_token: str  # raw one-time token (returned to the admin CLI only)
    expires_at: datetime


class SetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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
    integrity: Score1to5 = 3
    honesty: Score1to5 = 3
    responsibility: Score1to5 = 3
    respect: Score1to5 = 3
    school_effort: Score1to5 = 3
    citizenship: Score1to5 = 3
    notes: str | None = None


class BehaviorScoreUpdate(BaseModel):
    integrity: Score1to5 | None = None
    honesty: Score1to5 | None = None
    responsibility: Score1to5 | None = None
    respect: Score1to5 | None = None
    school_effort: Score1to5 | None = None
    citizenship: Score1to5 | None = None
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
    reward_amount: Cents = 0  # cents
    pillar: Pillar | None = None
    age_band: str | None = None
    category: str | None = None
    repeatable: Annotated[int, Field(ge=0, le=1)] = 0
    decay_divisor: Divisor = 2
    reset_days: Days | None = None


class BountyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    requirements: str | None = None
    reference: str | None = None
    criteria: str | None = None
    reward_amount: OptCents | None = None
    status: str | None = None
    pillar: Pillar | None = None
    age_band: str | None = None
    category: str | None = None
    repeatable: Annotated[int, Field(ge=0, le=1)] | None = None
    decay_divisor: Divisor | None = None
    reset_days: Days | None = None
    times_completed: Count | None = None
    streak_count: Count | None = None


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
    cost_cents: Cents = 0
    url: str | None = None
    priority: Annotated[int, Field(ge=1, le=10)] = 1

    _v_url = field_validator("url")(_validate_http_url)


class WishlistStatus(str, Enum):
    saving = "saving"
    approved = "approved"
    purchased = "purchased"


class WishlistUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    cost_cents: OptCents | None = None
    url: str | None = None
    priority: Annotated[int, Field(ge=1, le=10)] | None = None
    status: WishlistStatus | None = None

    _v_url = field_validator("url")(_validate_http_url)


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


# --- Gallery (canonical child media) ------------------------------------------


class MediaUpdate(BaseModel):
    """Editable metadata on a gallery item (not the bytes)."""

    observation: str | None = None
    age_band: str | None = None
    taken_at: datetime | None = None
    observed_at: datetime | None = None


class ObjectiveLinkCreate(BaseModel):
    objective_id: int


# --- Direct-to-S3 (large video) upload: initiate / finalize -------------------

# Pragmatic ceiling so a signed PUT can't be used to park an unbounded object.
MAX_DIRECT_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


class UploadInitiateRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: Annotated[int, Field(gt=0, le=MAX_DIRECT_UPLOAD_BYTES)]


class UploadInitiateResponse(BaseModel):
    media_id: int
    upload_url: str
    storage_key: str
    method: str = "PUT"


class UploadFinalizeRequest(BaseModel):
    # Optional metadata the client can attach at finalize time.
    observation: str | None = None
    age_band: str | None = None


class MediaObjectiveLinkResponse(BaseModel):
    id: int
    objective_id: int
    linked_at: datetime

    model_config = {"from_attributes": True}


class MediaResponse(BaseModel):
    id: int
    profile_id: int
    original_name: str
    mime_type: str
    media_type: str
    size_bytes: int
    taken_at: datetime | None = None
    observed_at: datetime | None = None
    observation: str | None = None
    age_band: str | None = None
    status: str
    created_at: datetime
    url: str | None = None  # resolved at serialization time (storage.url_for)
    objective_ids: list[int] = []

    model_config = {"from_attributes": True}


# --- Contacts / groups / share grants (v6 Pass 4) ----------------------------

CONTACT_ROLES = (
    "pediatrician",
    "speech_therapist",
    "occupational_therapist",
    "other_clinician",
    "educator",
    "childcare",
    "caregiver",
    "family",
    "guardian",
    "emergency_contact",
    "other",
)


def _validate_roles(v: str | None) -> str:
    """Comma-separated role keys; every key must be a known CONTACT_ROLE."""
    if not v:
        return "other"
    keys = [k.strip() for k in v.split(",") if k.strip()]
    bad = [k for k in keys if k not in CONTACT_ROLES]
    if bad:
        raise ValueError(f"Unknown contact role(s): {', '.join(bad)}")
    return ",".join(keys) or "other"


# Relationship sub-types, keyed by first-category role. Only roles present here
# get a (dependent) second dropdown in the UI; the rest have no sub-type.
RELATIONSHIP_SUBTYPES: dict[str, tuple[str, ...]] = {
    "family": (
        "mother",
        "father",
        "grandmother",
        "grandfather",
        "aunt",
        "uncle",
        "sibling",
        "cousin",
        "godparent",
        "stepmother",
        "stepfather",
        "stepsibling",
        "other",
    ),
    "guardian": (
        "mother",
        "father",
        "stepmother",
        "stepfather",
        "legal_guardian",
        "foster_parent",
        "godparent",
        "other",
    ),
    "other_clinician": (
        "therapist",
        "psychologist",
        "psychiatrist",
        "dentist",
        "optometrist",
        "dietitian",
        "specialist",
        "other",
    ),
    "educator": (
        "classroom_teacher",
        "special_education_teacher",
        "aide",
        "tutor",
        "administrator",
        "counselor",
        "coach",
        "other",
    ),
    "childcare": (
        "daycare_provider",
        "babysitter",
        "nanny",
        "after_school_program",
        "other",
    ),
    "emergency_contact": ("primary", "secondary", "other"),
}


def _first_role(roles: str) -> str:
    return (roles or "other").split(",")[0].strip() or "other"


def _check_subtype(roles: str, subtype: str | None) -> None:
    """Validate a relationship sub-type against the primary role.

    - A role with NO sub-types must not carry one.
    - A role WITH sub-types may be left blank, but any provided value must be in
      that role's allowed set.
    """
    if subtype is None or subtype == "":
        return
    role = _first_role(roles)
    allowed = RELATIONSHIP_SUBTYPES.get(role)
    if allowed is None:
        raise ValueError(f"Role '{role}' does not take a relationship sub-type")
    if subtype not in allowed:
        raise ValueError(f"'{subtype}' is not a valid sub-type for role '{role}'")


class ContactMethodCreate(BaseModel):
    channel: str  # email|sms
    address: str

    @field_validator("channel")
    @classmethod
    def _chan(cls, v: str) -> str:
        if v not in ("email", "sms"):
            raise ValueError("channel must be 'email' or 'sms'")
        return v


class ContactMethodResponse(BaseModel):
    id: int
    channel: str
    address: str
    verified_at: datetime | None = None
    active: int
    consent_at: datetime | None = None
    opted_out_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContactCreate(BaseModel):
    display_name: str
    kind: str = "individual"
    notes: str | None = None
    methods: list[ContactMethodCreate] = []
    # Role label + optional relationship sub-type, applied to this child's link.
    roles: str = "other"
    relationship_subtype: str | None = None

    _v_roles = field_validator("roles")(_validate_roles)

    @field_validator("relationship_subtype")
    @classmethod
    def _norm_subtype(cls, v: str | None) -> str | None:
        return v or None

    def validate_subtype_for_role(self) -> None:
        """Ensure the sub-type (if any) is valid for the primary role. Called by
        the route after validation so the role/subtype pair is consistent."""
        _check_subtype(self.roles, self.relationship_subtype)


class ContactUpdate(BaseModel):
    display_name: str | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    id: int
    display_name: str
    kind: str
    notes: str | None = None
    created_at: datetime
    methods: list[ContactMethodResponse] = []

    model_config = {"from_attributes": True}


class ProfileContactLinkCreate(BaseModel):
    contact_id: int
    roles: str = "other"
    relationship_subtype: str | None = None
    purpose: str | None = None
    default_disclosure: str = "minimal"

    _v_roles = field_validator("roles")(_validate_roles)

    @field_validator("default_disclosure")
    @classmethod
    def _disc(cls, v: str) -> str:
        if v not in ("minimal", "standard"):
            raise ValueError("default_disclosure must be 'minimal' or 'standard'")
        return v

    def validate_subtype_for_role(self) -> None:
        _check_subtype(self.roles, self.relationship_subtype)


class ProfileContactLinkResponse(BaseModel):
    id: int
    profile_id: int
    contact_id: int
    roles: str
    relationship_subtype: str | None = None
    purpose: str | None = None
    default_disclosure: str
    active: int
    added_at: datetime

    model_config = {"from_attributes": True}


class ContactGroupCreate(BaseModel):
    name: str


class ContactGroupResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    member_contact_ids: list[int] = []

    model_config = {"from_attributes": True}


class ShareGrantCreate(BaseModel):
    media_id: int
    # how long the link is valid; default 72h, capped at 7 days.
    expires_in_hours: Annotated[int, Field(gt=0, le=168)] = 72


class ShareGrantResponse(BaseModel):
    id: int
    media_id: int
    share_url: str  # contains the opaque token ONCE, at creation time
    expires_at: datetime
    revoked_at: datetime | None = None
    access_count: int

    model_config = {"from_attributes": True}


# --- Contact-method verification (email / SMS) -------------------------------


class VerifyStartResponse(BaseModel):
    method_id: int
    channel: str
    sent_to: str  # redacted destination
    backend: str  # console | ses | aws — tells the UI if it's live or dev
    # In console/dev mode only, the code is echoed so the flow is testable
    # WITHOUT a provider. Real backends (ses/aws) MUST leave this null.
    dev_code: str | None = None
    expires_at: datetime


class VerifyConfirmRequest(BaseModel):
    code: str


class VerifyConfirmResponse(BaseModel):
    method_id: int
    verified: bool
    verified_at: datetime | None = None
