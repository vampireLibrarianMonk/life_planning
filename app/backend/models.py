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
    civic = "civic"
    scientific_reality_testing = "scientific_reality_testing"
    inheritance_burden_stewardship = "inheritance_burden_stewardship"
    catholic_formation = "catholic_formation"
    secular_sacred_formation = "secular_sacred_formation"


class BountyTier(str, enum.Enum):
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(200), nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.readonly)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Contact/delivery address — NOT a login id (login stays username-based).
    email = Column(String(255), nullable=True)
    # Forces a password reset at next login (used for setup-link provisioning).
    must_change_password = Column(Integer, nullable=False, default=0)
    # One-time setup link: store only the SHA-256 hash of the token + expiry.
    setup_token_hash = Column(String(255), nullable=True)
    setup_token_expires = Column(DateTime, nullable=True)
    # Bumped to invalidate all outstanding JWTs for this user (logout-all /
    # password change). The JWT carries this as a `tv` claim; get_current_user
    # rejects a token whose tv != the current column value.
    token_version = Column(Integer, nullable=False, default=0)

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
    weekly_budget_cents = Column(Integer, nullable=True)  # max payout per week (null = no cap)
    monthly_budget_cents = Column(Integer, nullable=True)  # max payout per month (null = no cap)
    annual_budget_cents = Column(Integer, nullable=True)  # max payout per year (null = no cap)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")
    entries = relationship("PillarEntry", back_populates="profile")
    access_grants = relationship("ProfileAccess", back_populates="profile")
    behavior_scores = relationship("BehaviorScore", back_populates="profile")
    behavior_incidents = relationship("BehaviorIncident", back_populates="profile")
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
    parent_id = Column(
        Integer, ForeignKey("pillar_entries.id"), nullable=True
    )  # sub-entries nest under milestones
    pillar = Column(Enum(Pillar), nullable=False)
    entry_type = Column(String(20), default="milestone")  # milestone, event, note, evidence
    age_band = Column(String(10), nullable=True)  # e.g. "0-5", "6-12"
    age_years = Column(Integer, nullable=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # Foundation, Exploration, etc.
    score = Column(Integer, nullable=True)  # 1-5 optional rating
    is_milestone = Column(Integer, default=0)  # 1=framework goal, 0=user entry
    status = Column(
        String(20), default="not_started"
    )  # not_started, introduced, in_progress, practicing, complete, mastered
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="entries")
    attachments = relationship(
        "EventAttachment", back_populates="entry", cascade="all, delete-orphan"
    )
    children = relationship("PillarEntry", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("PillarEntry", back_populates="children", remote_side=[id])


class BehaviorScore(Base):
    """Weekly character/behavior scores that gate bounty eligibility."""

    __tablename__ = "behavior_scores"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    week_of = Column(String(10), nullable=False)  # YYYY-MM-DD (Monday of that week)
    integrity = Column(Integer, default=3)  # 1-5 (legacy, kept for backward compat)
    honesty = Column(Integer, default=3)
    responsibility = Column(Integer, default=3)
    respect = Column(Integer, default=3)
    school_effort = Column(Integer, default=3)
    citizenship = Column(Integer, default=3)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="behavior_scores")


class BehaviorIncident(Base):
    """A single positive or negative behavioral incident linked to a trait."""

    __tablename__ = "behavior_incidents"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    trait = Column(
        String(50), nullable=False
    )  # integrity, honesty, responsibility, respect, school_effort, citizenship
    positive = Column(Integer, default=1)  # 1=positive demonstration, 0=violation
    description = Column(String(500), nullable=False)  # what happened
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="behavior_incidents")


class Bounty(Base):
    """A bounty task that can be claimed and completed for reward."""

    __tablename__ = "bounties"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    pillar = Column(Enum(Pillar), nullable=True)  # optional link to a developmental pillar
    tier = Column(Enum(BountyTier), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)  # checklist of what must be done
    reference = Column(Text, nullable=True)  # study material, templates, standards
    criteria = Column(Text, nullable=True)  # how 'done' is judged
    reward_amount = Column(Integer, default=0)  # cents (original base amount)
    age_band = Column(String(10), nullable=True)  # e.g. "0-5", "6-12"
    category = Column(String(30), nullable=True)  # saint, paradox, effect, or null for standard
    repeatable = Column(Integer, default=0)  # 1=repeatable, 0=one-time
    decay_divisor = Column(Integer, default=2)  # divide reward by this each completion (2=halve)
    reset_days = Column(
        Integer, nullable=True
    )  # days after last completion before decay resets (null=never)
    times_completed = Column(Integer, default=0)  # how many times completed (for decay calc)
    streak_count = Column(Integer, default=0)  # consecutive on-time completions
    streak_best = Column(Integer, default=0)  # all-time best streak
    last_completed_at = Column(DateTime, nullable=True)  # for reset timer
    prerequisites = Column(Text, nullable=True)  # JSON list of bounty IDs that must be paid first
    status = Column(String(20), default="available")  # available, claimed, complete, paid
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="bounties")
    logs = relationship("BountyLog", back_populates="bounty", cascade="all, delete-orphan")


class BountyLog(Base):
    """Universal log entry for a bounty — notes, submissions, feedback, evidence."""

    __tablename__ = "bounty_logs"

    id = Column(Integer, primary_key=True, index=True)
    bounty_id = Column(Integer, ForeignKey("bounties.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(50), nullable=False)  # 'child' or 'parent'
    entry_type = Column(String(20), default="note")  # note, submission, feedback, evidence
    content = Column(Text, nullable=False)
    attachment = Column(String(500), nullable=True)  # filename in uploads/
    created_at = Column(DateTime, default=datetime.utcnow)

    bounty = relationship("Bounty", back_populates="logs")


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


class ProfileMedia(Base):
    """Canonical, child-scoped media (photo/video/document).

    This is the ONE private gallery per child. Media lives independently of any
    objective/age-group: deactivating an age group must NOT delete these rows
    (unlike the legacy EventAttachment cascade). Objective association is
    optional and modelled separately in MediaObjectiveLink.
    """

    __tablename__ = "profile_media"

    id = Column(Integer, primary_key=True, index=True)
    # Mandatory: every media item belongs to exactly one child profile.
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The user who uploaded it (for audit); not an authorization source.
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    storage_key = Column(String(500), nullable=False)  # key in the storage backend
    original_name = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    media_type = Column(String(20), nullable=False, default="other")  # photo|video|document|other
    size_bytes = Column(Integer, default=0)
    sha256 = Column(String(64), nullable=True)  # content hash (dedupe / integrity)
    # Independent timestamps: when it was captured vs. recorded in the app.
    taken_at = Column(DateTime, nullable=True)
    observed_at = Column(DateTime, nullable=True)
    observation = Column(Text, nullable=True)  # free-text note
    age_band = Column(String(10), nullable=True)  # optional convenience tag
    status = Column(String(20), nullable=False, default="ready")  # pending|ready|failed
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # soft delete

    profile = relationship("Profile")
    owner = relationship("User")
    objective_links = relationship(
        "MediaObjectiveLink", back_populates="media", cascade="all, delete-orphan"
    )


class MediaObjectiveLink(Base):
    """Optional association between a canonical media item and an objective entry.

    Deleting the objective (PillarEntry) removes ONLY this link row, never the
    underlying ProfileMedia. This is the decoupling that fixes the archive-loss
    risk documented in the v6 handoff.
    """

    __tablename__ = "media_objective_link"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id = Column(
        Integer, ForeignKey("profile_media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # If the objective row is deleted, drop the link but keep the media.
    objective_id = Column(
        Integer, ForeignKey("pillar_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    linked_at = Column(DateTime, default=datetime.utcnow)

    media = relationship("ProfileMedia", back_populates="objective_links")


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


class Discernment(Base):
    """A life-path choice the child is actively forming toward."""

    __tablename__ = "discernments"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    category = Column(String(50), nullable=False)  # career, vocation, education
    title = Column(String(300), nullable=False)  # e.g. "Software Engineering", "Military - Army"
    status = Column(String(30), default="exploring")  # exploring, committed, achieved, changed
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile")


class DiscernmentJournal(Base):
    """A reflective entry tracking the child's evolving understanding of a fundamental domain."""

    __tablename__ = "discernment_journal"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    category = Column(
        String(30), nullable=False
    )  # health, math, science, civics, relationships, faith
    title = Column(String(300), nullable=False)  # brief summary
    reflection = Column(Text, nullable=False)  # the child's written reflection
    age_at_entry = Column(Integer, nullable=True)  # child's age when written
    # Author of this entry: 'child' (the child's private diary — only the child
    # may read it) or 'admin' (a parent note — admin + child may read/CRUD).
    created_by = Column(String(20), nullable=False, default="child")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile")


class Fund(Base):
    """A tracked fund with a starting balance that draws down over time (e.g., insurance fund)."""

    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    starting_balance = Column(Integer, default=0)  # cents
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile")
    transactions = relationship(
        "FundTransaction", back_populates="fund", cascade="all, delete-orphan"
    )


class FundTransaction(Base):
    """A single disbursement or adjustment on a fund."""

    __tablename__ = "fund_transactions"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # cents (positive = disbursement/withdrawal)
    description = Column(String(500), nullable=False)
    date = Column(String(10), nullable=True)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)

    fund = relationship("Fund", back_populates="transactions")


class LessonPlan(Base):
    """A transcript-based lesson plan submitted by the admin for the child to study."""

    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    pillar = Column(Enum(Pillar), nullable=True)
    title = Column(String(500), nullable=False)
    source = Column(String(500), nullable=True)  # e.g., "YouTube: Channel Name" or "Book: Title"
    url = Column(String(1000), nullable=True)  # link to original video/article
    transcript = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)  # admin notes on what to focus on
    age_band = Column(String(10), nullable=True)
    status = Column(
        String(20), default="assigned"
    )  # assigned, in_progress, rebrief_done, expansion_done, teachback_done, complete
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile")
    responses = relationship(
        "LessonResponse", back_populates="lesson", cascade="all, delete-orphan"
    )


class LessonResponse(Base):
    """A child's response to a lesson plan (rebrief, expansion, or teachback)."""

    __tablename__ = "lesson_responses"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lesson_plans.id"), nullable=False)
    response_type = Column(String(20), nullable=False)  # rebrief, expansion, teachback
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lesson = relationship("LessonPlan", back_populates="responses")


# --- Contacts / groups / share grants (v6 Pass 4) ----------------------------
# Design invariants (from the v6 handoff):
#   * A contact is owner-scoped (the family account), NOT a login User.
#   * A contact must be EXPLICITLY linked to a child profile before it can be
#     used in that child's composer. The link carries role labels + a disclosure
#     policy. Classification/label NEVER grants data access on its own.
#   * Each contact METHOD (email/phone) is verified/consented independently.
#   * Share grants store a HASH of the token, never the raw token.

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


class Contact(Base):
    """A reusable person/organization the family may message. NOT a login."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # creating admin (audit)
    display_name = Column(String(200), nullable=False)
    kind = Column(String(20), nullable=False, default="individual")  # individual|organization
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    methods = relationship("ContactMethod", back_populates="contact", cascade="all, delete-orphan")
    profile_links = relationship(
        "ProfileContactLink", back_populates="contact", cascade="all, delete-orphan"
    )


class ContactMethod(Base):
    """An email or phone endpoint for a contact, verified/consented per method."""

    __tablename__ = "contact_methods"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel = Column(String(10), nullable=False)  # email|sms
    address = Column(String(320), nullable=False)  # email address or E.164 phone
    verified_at = Column(DateTime, nullable=True)
    verification_method = Column(String(40), nullable=True)
    # Pending verification challenge (code is stored HASHED, never in the clear).
    verify_code_hash = Column(String(64), nullable=True)
    verify_expires_at = Column(DateTime, nullable=True)
    verify_attempts = Column(Integer, nullable=False, default=0)
    active = Column(Integer, nullable=False, default=1)
    # SMS requires explicit opt-in consent (A2P). Email consent tracked too.
    consent_at = Column(DateTime, nullable=True)
    opted_out_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="methods")


class ProfileContactLink(Base):
    """Explicit association of a contact to ONE child profile.

    Required before the contact appears in that child's composer. Carries the
    role labels (comma-separated keys from CONTACT_ROLES) and a default
    disclosure policy. The link is the authorization anchor — labels alone are
    not authorization.
    """

    __tablename__ = "profile_contact_links"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id = Column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    roles = Column(String(300), nullable=False, default="other")  # CSV of CONTACT_ROLES
    # Optional relationship sub-type (e.g. family -> "mother"). Only meaningful
    # for roles that have sub-types (see RELATIONSHIP_SUBTYPES in schemas).
    relationship_subtype = Column(String(40), nullable=True)
    purpose = Column(String(300), nullable=True)
    # Minimum-necessary by default; clinical/private categories require explicit
    # opt-in per message, never auto-granted by a role label.
    default_disclosure = Column(String(20), nullable=False, default="minimal")  # minimal|standard
    active = Column(Integer, nullable=False, default=1)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="profile_links")


class ContactGroup(Base):
    """A named selection aid (e.g. 'Pediatric Care Team'). NOT a permission grant."""

    __tablename__ = "contact_groups"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship(
        "ContactGroupMember", back_populates="group", cascade="all, delete-orphan"
    )


class ContactGroupMember(Base):
    __tablename__ = "contact_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer, ForeignKey("contact_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id = Column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("ContactGroup", back_populates="members")


# --- Email Center (v6 Pass 5) -------------------------------------------------
# Design invariants (from the v6 handoff / backlog build plan):
#   * Drafts are mutable working copies; messages are IMMUTABLE snapshots.
#   * One draft = ONE audience class (family OR clinician OR educator) — mixed
#     audiences are forced into separate drafts by the disclosure validator.
#   * Per-recipient Message rows (never a blended To/Cc list).
#   * Idempotency key on Message makes a provider retry non-duplicating.
#   * Private worries (child_development_private) are structurally excluded.


class MessageDraft(Base):
    """A compose-in-progress email. Mutable until sent."""

    __tablename__ = "message_drafts"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel = Column(String(10), nullable=False, default="email")  # email (sms later)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # composing admin
    # Single audience class per draft (disclosure policy anchor): family |
    # clinician | educator. Derived from the selected recipients' roles.
    audience = Column(String(20), nullable=False, default="family")
    # Recipient contact-method ids (JSON list). Re-resolved + re-verified at
    # preview/send time; the snapshot stored on Message is what actually went.
    recipient_method_ids = Column(Text, nullable=False, default="[]")
    subject = Column(String(300), nullable=False, default="")
    body = Column(Text, nullable=False, default="")
    # Gallery media ids (JSON list) selected for this update.
    selected_media_ids = Column(Text, nullable=False, default="[]")
    template_key = Column(String(60), nullable=True)  # e.g. family_update
    # Explicit opt-in for clinical content (clinician audience only).
    include_clinical = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="draft")  # draft | sent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile")


class Message(Base):
    """An actually-dispatched (or attempted) message. Immutable after send.

    recipient_snapshot / content_snapshot freeze exactly what was sent so the
    Sent history is an honest audit trail. One row PER RECIPIENT (groups are
    expanded; no cross-recipient address exposure).
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id = Column(Integer, ForeignKey("message_drafts.id"), nullable=True, index=True)
    channel = Column(String(10), nullable=False, default="email")
    sender = Column(String(320), nullable=True)  # From identity used (SES) or 'console'
    recipient_contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    recipient_address = Column(String(320), nullable=False)
    # JSON snapshots (immutable after send).
    recipient_snapshot = Column(Text, nullable=False, default="{}")
    content_snapshot = Column(Text, nullable=False, default="{}")
    transport = Column(String(20), nullable=False, default="console")  # console | ses
    provider_id = Column(String(200), nullable=True)  # SES MessageId (SUBMITTED evidence)
    # Unique per (draft, recipient): a retry reuses the same key so a timeout
    # followed by a re-send cannot produce a duplicate billable send.
    idempotency_key = Column(String(120), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default="queued")  # queued|submitted|failed
    sent_at = Column(DateTime, nullable=True)
    status_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageEvent(Base):
    """Provider lifecycle event for a message (send/bounce/complaint/delivery)."""

    __tablename__ = "message_events"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_event_id = Column(String(200), nullable=True)
    type = Column(String(40), nullable=False)  # sent | bounce | complaint | delivery
    raw = Column(Text, nullable=True)  # provider payload (signature-verified upstream)
    created_at = Column(DateTime, default=datetime.utcnow)


class OutboxJob(Base):
    """Dispatch bookkeeping for at-most-once sending (retry/reconcile anchor)."""

    __tablename__ = "outbox_jobs"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state = Column(String(20), nullable=False, default="pending")  # pending|done|failed
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MediaShareGrant(Base):
    """A revocable, expiring grant that lets a recipient view one media item via
    an opaque app link. The raw token is NEVER stored — only its SHA-256 hash."""

    __tablename__ = "media_share_grants"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id = Column(
        Integer, ForeignKey("profile_media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)  # sha256 hex
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
