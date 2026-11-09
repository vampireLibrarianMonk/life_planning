"""Contacts / groups / share grants (v6 Pass 4) — adversarial + behavior tests.

Route-function level, matching the repo convention. Covers the Critical/High
release-gate cases from the v6 handoff that apply to this pass:

  CONTACT-01  a contact linked to Child A is NOT usable for Child B
  CONTACT-05/role  role LABEL never grants data access (link is the anchor)
  SHARE-01    expired token denied
  SHARE-02    revoked token denied
  SHARE-03    raw token never stored (only its hash)
  AUTH        cross-profile share creation denied
  group       a contact must be linked to the profile before joining a group
"""

import hashlib
import importlib
import sys
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in (
        "config",
        "database",
        "models",
        "auth",
        "storage",
        "main",
        "routes.contacts",
        "routes.gallery",
    ):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    contacts = importlib.import_module("routes.contacts")

    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()
    monkeypatch.setattr(storage.LocalStorage, "__init__", lambda self: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    database.Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    a = models.Profile(name="Child A", date_of_birth="2015-01-01")
    b = models.Profile(name="Child B", date_of_birth="2016-02-02")
    db.add_all([a, b])
    db.flush()
    admin = models.User(
        username="admin", hashed_password="x", display_name="A", role=models.Role.admin, id=1
    )
    db.add(admin)
    db.commit()
    return contacts, models, storage, db, a.id, b.id, admin


def _make_contact(contacts, db, pid, admin, name="Dr. Sample", roles="pediatrician"):
    from schemas import ContactCreate, ContactMethodCreate

    c = contacts.create_contact(
        pid,
        ContactCreate(
            display_name=name,
            methods=[ContactMethodCreate(channel="email", address="dr@example.com")],
        ),
        db=db,
        current_user=admin,
    )
    return c


def test_contact_created_and_listed_for_its_profile_only(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    _make_contact(contacts, db, a, admin)
    assert len(contacts.list_contacts(a, db=db)) == 1
    # Child B has no contacts — the directory is per-child-linked.
    assert contacts.list_contacts(b, db=db) == []


def test_contact01_contact_linked_to_a_not_usable_for_b(ctx):
    """A pediatrician linked to Child A must not appear for Child B, and a share
    cannot be made for B using A's contact context."""
    contacts, models, storage, db, a, b, admin = ctx
    c = _make_contact(contacts, db, a, admin)
    # B's address book does not contain it.
    assert all(x.id != c.id for x in contacts.list_contacts(b, db=db))
    # And fetching/patching it under B is denied.
    from schemas import ContactUpdate

    with pytest.raises(HTTPException) as e:
        contacts.update_contact(b, c.id, ContactUpdate(display_name="x"), db=db, _=admin)
    assert e.value.status_code == 404


def test_role_label_is_not_authorization(ctx):
    """Linking a contact as 'family' vs 'pediatrician' only sets a label; it does
    not itself grant any data. We assert the link stores the label verbatim and
    the disclosure default stays 'minimal' regardless of label."""
    contacts, models, storage, db, a, b, admin = ctx
    c = _make_contact(contacts, db, a, admin)
    from schemas import ProfileContactLinkCreate

    link = contacts.link_existing_contact(
        b,
        ProfileContactLinkCreate(contact_id=c.id, roles="pediatrician,family"),
        db=db,
        current_user=admin,
    )
    assert link.roles == "pediatrician,family"
    assert link.default_disclosure == "minimal"  # label did NOT upgrade disclosure


def test_unknown_role_rejected(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    import pydantic

    from schemas import ProfileContactLinkCreate

    with pytest.raises(pydantic.ValidationError):
        ProfileContactLinkCreate(contact_id=1, roles="pediatrician,hacker")


def test_contact_with_both_email_and_phone(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ContactCreate, ContactMethodCreate

    c = contacts.create_contact(
        a,
        ContactCreate(
            display_name="Two Methods",
            methods=[
                ContactMethodCreate(channel="email", address="x@example.com"),
                ContactMethodCreate(channel="sms", address="+15555550123"),
            ],
            roles="family",
            relationship_subtype="mother",
        ),
        db=db,
        current_user=admin,
    )
    channels = sorted(m.channel for m in c.methods)
    assert channels == ["email", "sms"]
    link = db.query(models.ProfileContactLink).filter_by(profile_id=a, contact_id=c.id).first()
    assert link.relationship_subtype == "mother"


def test_relationship_subtype_valid_for_role_persists(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ContactCreate

    c = contacts.create_contact(
        a,
        ContactCreate(display_name="Gran", roles="family", relationship_subtype="grandmother"),
        db=db,
        current_user=admin,
    )
    link = db.query(models.ProfileContactLink).filter_by(contact_id=c.id).first()
    assert link.relationship_subtype == "grandmother"


def test_subtype_invalid_for_role_rejected(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from fastapi import HTTPException

    from schemas import ContactCreate

    # pediatrician has NO sub-types -> providing one is a 422.
    with pytest.raises(HTTPException) as e:
        contacts.create_contact(
            a,
            ContactCreate(display_name="Dr", roles="pediatrician", relationship_subtype="mother"),
            db=db,
            current_user=admin,
        )
    assert e.value.status_code == 422


def test_subtype_wrong_value_for_role_rejected(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from fastapi import HTTPException

    from schemas import ContactCreate

    # 'ceo' is not a valid family sub-type.
    with pytest.raises(HTTPException) as e:
        contacts.create_contact(
            a,
            ContactCreate(display_name="X", roles="family", relationship_subtype="ceo"),
            db=db,
            current_user=admin,
        )
    assert e.value.status_code == 422


def test_relationship_subtypes_map_shape(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    m = contacts.relationship_subtypes(a)
    # Roles with sub-types present; roles without are absent (no 2nd dropdown).
    assert "mother" in m["family"] and "godparent" in m["family"] and "stepmother" in m["family"]
    assert "pediatrician" not in m
    assert "speech_therapist" not in m


def test_group_member_must_be_linked_to_profile(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ContactGroupCreate

    c = _make_contact(contacts, db, a, admin)  # linked to A only
    grp = contacts.create_group(b, ContactGroupCreate(name="Care Team"), db=db, current_user=admin)
    # Adding A's contact to a group under B must fail (not linked to B).
    with pytest.raises(HTTPException) as e:
        contacts.add_group_member(b, grp.id, c.id, db=db, _=admin)
    assert e.value.status_code == 404


# --- Share grants ------------------------------------------------------------


def _make_media(models, storage, db, pid):
    st = storage.get_storage()
    st.save("k_share.jpg", b"IMG", "image/jpeg")
    m = models.ProfileMedia(
        profile_id=pid,
        storage_key="k_share.jpg",
        original_name="x.jpg",
        mime_type="image/jpeg",
        media_type="photo",
        status="ready",
    )
    db.add(m)
    db.commit()
    return m


def test_share_token_is_hashed_not_stored_raw(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ShareGrantCreate

    m = _make_media(models, storage, db, a)
    grant = contacts.create_share(a, ShareGrantCreate(media_id=m.id), db=db, current_user=admin)
    raw = grant.share_url.rsplit("/", 1)[-1]
    row = db.query(models.MediaShareGrant).filter_by(id=grant.id).first()
    # DB stores only the sha256 of the token, never the token itself.
    assert row.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in (row.token_hash or "")


def test_share01_expired_token_denied(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ShareGrantCreate

    m = _make_media(models, storage, db, a)
    grant = contacts.create_share(a, ShareGrantCreate(media_id=m.id), db=db, current_user=admin)
    raw = grant.share_url.rsplit("/", 1)[-1]
    # Force-expire it.
    row = db.query(models.MediaShareGrant).filter_by(id=grant.id).first()
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    with pytest.raises(HTTPException) as e:
        contacts.resolve_share(raw, db=db)
    assert e.value.status_code == 404


def test_share02_revoked_token_denied(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ShareGrantCreate

    m = _make_media(models, storage, db, a)
    grant = contacts.create_share(a, ShareGrantCreate(media_id=m.id), db=db, current_user=admin)
    raw = grant.share_url.rsplit("/", 1)[-1]
    contacts.revoke_share(a, grant.id, db=db, _=admin)
    with pytest.raises(HTTPException) as e:
        contacts.resolve_share(raw, db=db)
    assert e.value.status_code == 404


def test_valid_share_resolves_and_counts(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ShareGrantCreate

    m = _make_media(models, storage, db, a)
    grant = contacts.create_share(a, ShareGrantCreate(media_id=m.id), db=db, current_user=admin)
    raw = grant.share_url.rsplit("/", 1)[-1]
    resp = contacts.resolve_share(raw, db=db)
    assert resp.status_code == 307  # redirect to a short-lived media URL
    row = db.query(models.MediaShareGrant).filter_by(id=grant.id).first()
    assert row.access_count == 1


def test_share_cross_profile_create_denied(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    from schemas import ShareGrantCreate

    m = _make_media(models, storage, db, a)  # media belongs to A
    with pytest.raises(HTTPException) as e:
        contacts.create_share(b, ShareGrantCreate(media_id=m.id), db=db, current_user=admin)
    assert e.value.status_code == 404


def test_garbage_share_token_denied(ctx):
    contacts, models, storage, db, a, b, admin = ctx
    with pytest.raises(HTTPException) as e:
        contacts.resolve_share("not-a-real-token", db=db)
    assert e.value.status_code == 404


# --- Contact-method verification (email / SMS) -------------------------------


def _contact_with_email(contacts, db, pid, admin, addr="dr@example.com"):
    from schemas import ContactCreate, ContactMethodCreate

    return contacts.create_contact(
        pid,
        ContactCreate(
            display_name="Dr. V",
            methods=[ContactMethodCreate(channel="email", address=addr)],
            roles="pediatrician",
        ),
        db=db,
        current_user=admin,
    )


def _method_id(db, models, contact_id):
    return db.query(models.ContactMethod).filter_by(contact_id=contact_id).first().id


def test_verify_happy_path_console(ctx, monkeypatch):
    """Console backend echoes the dev code so the flow is fully testable; the
    code verifies and flips verified_at + clears the challenge."""
    contacts, models, storage, db, a, b, admin = ctx
    import notify

    monkeypatch.setenv("NOTIFY_EMAIL_BACKEND", "console")
    notify.reset_senders()

    c = _contact_with_email(contacts, db, a, admin)
    mid = _method_id(db, models, c.id)
    start = contacts.start_verification(a, c.id, mid, db=db, _=admin)
    assert start.backend == "console" and start.dev_code is not None

    from schemas import VerifyConfirmRequest

    out = contacts.confirm_verification(
        a, c.id, mid, VerifyConfirmRequest(code=start.dev_code), db=db, _=admin
    )
    assert out.verified is True and out.verified_at is not None
    row = db.query(models.ContactMethod).get(mid)
    assert row.verified_at is not None
    assert row.verify_code_hash is None  # challenge cleared
    assert row.verification_method == "code_email"


def test_verify_wrong_code_counts_attempt_then_locks(ctx, monkeypatch):
    contacts, models, storage, db, a, b, admin = ctx
    import notify

    notify.reset_senders()
    c = _contact_with_email(contacts, db, a, admin)
    mid = _method_id(db, models, c.id)
    contacts.start_verification(a, c.id, mid, db=db, _=admin)

    from schemas import VerifyConfirmRequest

    for _ in range(5):
        with pytest.raises(HTTPException) as e:
            contacts.confirm_verification(
                a, c.id, mid, VerifyConfirmRequest(code="000000"), db=db, _=admin
            )
        assert e.value.status_code == 400  # incorrect code
    # 6th attempt is locked out (attempt cap).
    with pytest.raises(HTTPException) as e:
        contacts.confirm_verification(
            a, c.id, mid, VerifyConfirmRequest(code="000000"), db=db, _=admin
        )
    assert e.value.status_code == 429
    assert db.query(models.ContactMethod).get(mid).verified_at is None


def test_verify_expired_code_rejected(ctx, monkeypatch):
    contacts, models, storage, db, a, b, admin = ctx
    from datetime import datetime, timedelta

    import notify

    notify.reset_senders()
    c = _contact_with_email(contacts, db, a, admin)
    mid = _method_id(db, models, c.id)
    start = contacts.start_verification(a, c.id, mid, db=db, _=admin)
    # Force-expire.
    row = db.query(models.ContactMethod).get(mid)
    row.verify_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    from schemas import VerifyConfirmRequest

    with pytest.raises(HTTPException) as e:
        contacts.confirm_verification(
            a, c.id, mid, VerifyConfirmRequest(code=start.dev_code), db=db, _=admin
        )
    assert e.value.status_code == 400


def test_verify_confirm_without_start_rejected(ctx, monkeypatch):
    contacts, models, storage, db, a, b, admin = ctx
    import notify

    notify.reset_senders()
    c = _contact_with_email(contacts, db, a, admin)
    mid = _method_id(db, models, c.id)
    from schemas import VerifyConfirmRequest

    with pytest.raises(HTTPException) as e:
        contacts.confirm_verification(
            a, c.id, mid, VerifyConfirmRequest(code="123456"), db=db, _=admin
        )
    assert e.value.status_code == 400


def test_verify_real_backend_not_provisioned_is_503(ctx, monkeypatch):
    """Selecting the SES backend WITHOUT a sender identity must fail honestly
    (503) and NOT fabricate a sent code."""
    contacts, models, storage, db, a, b, admin = ctx
    import notify

    monkeypatch.setenv("NOTIFY_EMAIL_BACKEND", "ses")
    monkeypatch.delenv("NOTIFY_EMAIL_FROM", raising=False)
    notify.reset_senders()

    c = _contact_with_email(contacts, db, a, admin)
    mid = _method_id(db, models, c.id)
    with pytest.raises(HTTPException) as e:
        contacts.start_verification(a, c.id, mid, db=db, _=admin)
    assert e.value.status_code == 503
    # No pending challenge was left behind.
    row = db.query(models.ContactMethod).get(mid)
    assert row.verify_code_hash is None and row.verified_at is None
    notify.reset_senders()


def test_verify_cross_profile_denied(ctx, monkeypatch):
    contacts, models, storage, db, a, b, admin = ctx
    import notify

    notify.reset_senders()
    c = _contact_with_email(contacts, db, a, admin)  # linked to A only
    mid = _method_id(db, models, c.id)
    with pytest.raises(HTTPException) as e:
        contacts.start_verification(b, c.id, mid, db=db, _=admin)
    assert e.value.status_code == 404
