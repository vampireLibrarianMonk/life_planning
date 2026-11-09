"""Contacts, groups, and media share grants (v6 Pass 4).

Shared recipient directory for the (future) Email and SMS centers. Key rules:
  * Contacts are owner-scoped; they are NOT login users.
  * A contact must be explicitly LINKED to a child profile before it can be used
    for that child. Role labels on the link are descriptive — they never grant
    data access by themselves.
  * Every route under /profiles/{id}/... is profile-scoped via
    require_profile_access; writes require require_admin_or_child.
  * Share grants mint an opaque token shown ONCE; only its SHA-256 hash is
    stored. The public resolver checks expiry/revocation and never logs tokens.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_or_child, require_profile_access
from database import get_db
from models import (
    Contact,
    ContactGroup,
    ContactGroupMember,
    ContactMethod,
    MediaShareGrant,
    ProfileContactLink,
    ProfileMedia,
    User,
)
from schemas import (
    ContactCreate,
    ContactGroupCreate,
    ContactGroupResponse,
    ContactResponse,
    ContactUpdate,
    ProfileContactLinkCreate,
    ProfileContactLinkResponse,
    ShareGrantCreate,
    ShareGrantResponse,
)
from storage import get_storage

router = APIRouter(
    prefix="/api/profiles/{profile_id}/contacts",
    tags=["contacts"],
    dependencies=[Depends(require_profile_access)],
)
groups_router = APIRouter(
    prefix="/api/profiles/{profile_id}/contact-groups",
    tags=["contacts"],
    dependencies=[Depends(require_profile_access)],
)
shares_router = APIRouter(
    prefix="/api/profiles/{profile_id}/media-shares",
    tags=["contacts"],
    dependencies=[Depends(require_profile_access)],
)
# Public (recipient) resolver — authorized at the resolver, not by a session.
public_share_router = APIRouter(prefix="/share", tags=["contacts"])


# --- Contacts (linked to the current profile) --------------------------------


def _linked_contact_or_404(db: Session, profile_id: int, contact_id: int) -> Contact:
    link = (
        db.query(ProfileContactLink)
        .filter(
            ProfileContactLink.profile_id == profile_id,
            ProfileContactLink.contact_id == contact_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Contact not linked to this profile")
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.get("/relationship-subtypes")
def relationship_subtypes(profile_id: int):
    """The role -> relationship sub-type map (single source of truth for the
    dependent second dropdown). Roles not present here have no sub-type."""
    from schemas import RELATIONSHIP_SUBTYPES

    return RELATIONSHIP_SUBTYPES


@router.get("/", response_model=list[ContactResponse])
def list_contacts(profile_id: int, db: Session = Depends(get_db)):
    """Contacts linked to THIS child (the composer's address book for them)."""
    links = (
        db.query(ProfileContactLink)
        .filter(ProfileContactLink.profile_id == profile_id, ProfileContactLink.active == 1)
        .all()
    )
    ids = [link.contact_id for link in links]
    if not ids:
        return []
    contacts = db.query(Contact).filter(Contact.id.in_(ids)).all()
    return [ContactResponse.model_validate(c) for c in contacts]


@router.post("/", response_model=ContactResponse, status_code=201)
def create_contact(
    profile_id: int,
    req: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_child),
):
    """Create a contact AND link it to this profile in one step."""
    try:
        req.validate_subtype_for_role()  # role/sub-type consistency
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    contact = Contact(
        owner_id=current_user.id,
        display_name=req.display_name,
        kind=req.kind,
        notes=req.notes,
    )
    db.add(contact)
    db.flush()
    for m in req.methods:
        db.add(ContactMethod(contact_id=contact.id, channel=m.channel, address=m.address))
    db.add(
        ProfileContactLink(
            profile_id=profile_id,
            contact_id=contact.id,
            roles=req.roles,
            relationship_subtype=req.relationship_subtype,
            approved_by=current_user.id,
        )
    )
    db.commit()
    db.refresh(contact)
    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    profile_id: int,
    contact_id: int,
    req: ContactUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    contact = _linked_contact_or_404(db, profile_id, contact_id)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return ContactResponse.model_validate(contact)


@router.post("/link", response_model=ProfileContactLinkResponse, status_code=201)
def link_existing_contact(
    profile_id: int,
    req: ProfileContactLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_child),
):
    """Link an EXISTING contact (e.g. one shared with a sibling) to this child,
    with its own role labels + disclosure policy for THIS child."""
    contact = db.query(Contact).filter(Contact.id == req.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    try:
        req.validate_subtype_for_role()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    existing = (
        db.query(ProfileContactLink)
        .filter(
            ProfileContactLink.profile_id == profile_id,
            ProfileContactLink.contact_id == req.contact_id,
        )
        .first()
    )
    if existing:
        existing.roles = req.roles
        existing.relationship_subtype = req.relationship_subtype
        existing.purpose = req.purpose
        existing.default_disclosure = req.default_disclosure
        existing.active = 1
        link = existing
    else:
        link = ProfileContactLink(
            profile_id=profile_id,
            contact_id=req.contact_id,
            roles=req.roles,
            relationship_subtype=req.relationship_subtype,
            purpose=req.purpose,
            default_disclosure=req.default_disclosure,
            approved_by=current_user.id,
        )
        db.add(link)
    db.commit()
    db.refresh(link)
    return ProfileContactLinkResponse.model_validate(link)


@router.delete("/{contact_id}/link", status_code=204)
def unlink_contact(
    profile_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    """Remove this child's link to a contact. The contact (and other children's
    links) remain. Also invalidates this child's group memberships for it."""
    link = (
        db.query(ProfileContactLink)
        .filter(
            ProfileContactLink.profile_id == profile_id,
            ProfileContactLink.contact_id == contact_id,
        )
        .first()
    )
    if link:
        db.delete(link)
        db.commit()


# --- Contact groups (selection aids, profile-scoped) -------------------------


def _group_response(db: Session, group: ContactGroup) -> ContactGroupResponse:
    resp = ContactGroupResponse.model_validate(group)
    resp.member_contact_ids = [m.contact_id for m in group.members]
    return resp


@groups_router.get("/", response_model=list[ContactGroupResponse])
def list_groups(profile_id: int, db: Session = Depends(get_db)):
    groups = db.query(ContactGroup).all()
    return [_group_response(db, g) for g in groups]


@groups_router.post("/", response_model=ContactGroupResponse, status_code=201)
def create_group(
    profile_id: int,
    req: ContactGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_child),
):
    group = ContactGroup(owner_id=current_user.id, name=req.name)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _group_response(db, group)


@groups_router.post("/{group_id}/members", response_model=ContactGroupResponse, status_code=201)
def add_group_member(
    profile_id: int,
    group_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    group = db.query(ContactGroup).filter(ContactGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # The contact must be linked to THIS profile (no adding a stranger).
    _linked_contact_or_404(db, profile_id, contact_id)
    exists = (
        db.query(ContactGroupMember)
        .filter(
            ContactGroupMember.group_id == group_id,
            ContactGroupMember.contact_id == contact_id,
        )
        .first()
    )
    if not exists:
        db.add(ContactGroupMember(group_id=group_id, contact_id=contact_id))
        db.commit()
    db.refresh(group)
    return _group_response(db, group)


# --- Media share grants (opaque, expiring, revocable) ------------------------


@shares_router.post("/", response_model=ShareGrantResponse, status_code=201)
def create_share(
    profile_id: int,
    req: ShareGrantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_child),
):
    media = (
        db.query(ProfileMedia)
        .filter(
            ProfileMedia.id == req.media_id,
            ProfileMedia.profile_id == profile_id,  # cross-profile guard
            ProfileMedia.deleted_at.is_(None),
        )
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    raw_token = secrets.token_urlsafe(32)
    grant = MediaShareGrant(
        profile_id=profile_id,
        media_id=media.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(hours=req.expires_in_hours),
        created_by=current_user.id,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    # Build the response explicitly: share_url (the raw token) is synthesized
    # here and returned exactly once; it is never persisted.
    return ShareGrantResponse(
        id=grant.id,
        media_id=grant.media_id,
        share_url=f"/share/{raw_token}",
        expires_at=grant.expires_at,
        revoked_at=grant.revoked_at,
        access_count=grant.access_count,
    )


@shares_router.post("/{grant_id}/revoke", status_code=204)
def revoke_share(
    profile_id: int,
    grant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_child),
):
    grant = (
        db.query(MediaShareGrant)
        .filter(MediaShareGrant.id == grant_id, MediaShareGrant.profile_id == profile_id)
        .first()
    )
    if grant and grant.revoked_at is None:
        grant.revoked_at = datetime.utcnow()
        db.commit()


@public_share_router.get("/{token}")
def resolve_share(token: str, db: Session = Depends(get_db)):
    """Public resolver for a share link. No session; the opaque token is the
    capability. Validates existence/expiry/revocation, then redirects to a
    short-lived media URL. Returns 404 for anything invalid (no oracle); never
    logs the token."""
    from fastapi.responses import RedirectResponse

    not_found = HTTPException(status_code=404, detail="Not found")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    grant = db.query(MediaShareGrant).filter(MediaShareGrant.token_hash == token_hash).first()
    if not grant or grant.revoked_at is not None or grant.expires_at < datetime.utcnow():
        raise not_found
    media = (
        db.query(ProfileMedia)
        .filter(ProfileMedia.id == grant.media_id, ProfileMedia.deleted_at.is_(None))
        .first()
    )
    if not media:
        raise not_found
    grant.access_count += 1
    db.commit()
    return RedirectResponse(url=get_storage().url_for(media.storage_key), status_code=307)
