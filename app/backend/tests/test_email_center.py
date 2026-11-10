"""Email Center (v6 Pass 5) - adversarial + behavior tests.

Route-function level, matching the repo convention. Release-gate cases:

  CONTACT-03  a family-audience draft must NOT expose clinical content
  PRIV-04     private worries never enter a draft (structural + content)
  mixed       mixed audiences forced into SEPARATE drafts
  MAIL-01     no send without explicit confirm
  MAIL-02     oversize image converts to a link (never dropped)
  MAIL-03     retry after send causes no duplicate (idempotency)
  AUTH        readonly/child cannot compose or send; cross-profile denied
  AI          Bedrock drafts: flag-gated, never auto-sent, policy-checked
"""

import importlib
import json
import sys
from datetime import datetime

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    monkeypatch.setenv("NOTIFY_EMAIL_BACKEND", "console")
    for mod in (
        "config",
        "database",
        "models",
        "auth",
        "storage",
        "main",
        "email_center",
        "notify",
        "routes.contacts",
        "routes.gallery",
        "routes.email_center",
    ):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    ec_routes = importlib.import_module("routes.email_center")
    contacts = importlib.import_module("routes.contacts")
    notify = importlib.import_module("notify")
    notify.reset_senders()

    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()
    monkeypatch.setattr(storage.LocalStorage, "__init__", lambda self: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    database.Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    a = models.Profile(name="Robert Test", date_of_birth="2022-01-01")
    b = models.Profile(name="Child B", date_of_birth="2016-02-02")
    db.add_all([a, b])
    db.flush()
    admin = models.User(
        username="admin", hashed_password="x", display_name="A", role=models.Role.admin, id=1
    )
    readonly = models.User(
        username="ro", hashed_password="x", display_name="R", role=models.Role.readonly, id=2
    )
    child = models.User(
        username="kid", hashed_password="x", display_name="K", role=models.Role.child, id=3
    )
    db.add_all([admin, readonly, child])
    db.commit()
    return {
        "routes": ec_routes,
        "contacts": contacts,
        "models": models,
        "storage": storage,
        "notify": notify,
        "db": db,
        "a": a.id,
        "b": b.id,
        "admin": admin,
        "readonly": readonly,
        "child": child,
    }


def _family_contact(ctx, name="Grandma Sara", addr="grandma@example.com"):
    return ctx["contacts"].create_contact(
        ctx["a"],
        __import__("schemas").ContactCreate(
            display_name=name,
            methods=[__import__("schemas").ContactMethodCreate(channel="email", address=addr)],
            roles="family",
        ),
        db=ctx["db"],
        current_user=ctx["admin"],
    )


def _verified_method_id(ctx, contact_id):
    db = ctx["db"]
    m = db.query(ctx["models"].ContactMethod).filter_by(contact_id=contact_id).first()
    m.verified_at = datetime.utcnow()
    db.commit()
    return m.id


def _objective(
    ctx, title="Stacks three blocks", status="complete", category="child_development:motor"
):
    db = ctx["db"]
    e = ctx["models"].PillarEntry(
        profile_id=ctx["a"],
        pillar="education",
        entry_type="milestone",
        title=title,
        status=status,
        category=category,
        age_band="12mo",
        age_years=1,
        is_milestone=1,
    )
    db.add(e)
    db.commit()
    return e


def _media(ctx, kind="photo", size=200_000, name="sample.jpg"):
    db = ctx["db"]
    m = ctx["models"].ProfileMedia(
        profile_id=ctx["a"],
        storage_key=f"k_{name}",
        original_name=name,
        mime_type="image/jpeg" if kind == "photo" else "video/mp4",
        media_type=kind,
        size_bytes=size,
        status="ready",
    )
    db.add(m)
    db.commit()
    return m


def _draft(ctx, method_id, media_ids=None, body=None, audience=None, fact_ids=None):
    from schemas import DraftCreate

    kwargs = dict(recipient_method_ids=[method_id], media_ids=media_ids or [])
    if audience:
        kwargs["audience"] = audience
    if body is not None:
        kwargs["body"] = body
    if fact_ids:
        kwargs["fact_ids"] = fact_ids
    return ctx["routes"].create_draft(
        ctx["a"], DraftCreate(**kwargs), db=ctx["db"], current_user=ctx["admin"]
    )


# --- Disclosure policy gates ---------------------------------------------------


def test_contact03_clinical_content_rejected_for_family(ctx):
    """A family-audience draft containing clinical vocabulary is REJECTED."""
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    with pytest.raises(HTTPException) as e:
        _draft(ctx, mid, body="She started speech therapy last week.")
    assert e.value.status_code == 422


def test_contact03_clinical_requires_clinician_audience_and_flag(ctx):
    """include_clinical on a non-clinician audience is rejected."""
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    from schemas import DraftCreate

    with pytest.raises(HTTPException) as e:
        ctx["routes"].create_draft(
            ctx["a"],
            DraftCreate(recipient_method_ids=[mid], include_clinical=True, body="Progress notes."),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    assert e.value.status_code == 422


def test_priv04_private_worries_body_rejected(ctx):
    """A draft body containing the private worries text verbatim is rejected."""
    db = ctx["db"]
    db.add(
        ctx["models"].PillarEntry(
            profile_id=ctx["a"],
            pillar="education",
            title="Worries",
            content="He still fights every diaper change.",
            status="complete",
            category="child_development_private",
            is_milestone=0,
        )
    )
    db.commit()
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    with pytest.raises(HTTPException) as e:
        _draft(ctx, mid, body="Update: He still fights every diaper change.")
    assert e.value.status_code == 422


def test_priv04_private_worries_never_in_fact_sheet(ctx):
    """The composer's fact sheet structurally EXCLUDES private worries."""
    _objective(ctx, title="Public objective", category="child_development:motor")
    db = ctx["db"]
    db.add(
        ctx["models"].PillarEntry(
            profile_id=ctx["a"],
            pillar="education",
            title="Private worry",
            content="secret-worry-payload",
            status="complete",
            category="child_development_private",
            is_milestone=1,
        )
    )
    db.commit()
    facts = ctx["routes"].list_facts(ctx["a"], db=db)
    titles = [h["title"] for h in facts["highlights"]]
    assert "Public objective" in titles
    assert "secret-worry-payload" not in json.dumps(facts)
    assert facts["private_worries_included"] is False


def test_mixed_audiences_forced_into_separate_drafts(ctx):
    """Selecting a family + a clinician recipient in ONE draft is rejected."""
    fam = _family_contact(ctx)
    clin = ctx["contacts"].create_contact(
        ctx["a"],
        __import__("schemas").ContactCreate(
            display_name="Dr. Sample",
            methods=[
                __import__("schemas").ContactMethodCreate(channel="email", address="dr@example.com")
            ],
            roles="pediatrician",
        ),
        db=ctx["db"],
        current_user=ctx["admin"],
    )
    m1 = _verified_method_id(ctx, fam.id)
    m2 = _verified_method_id(ctx, clin.id)
    from schemas import DraftCreate

    with pytest.raises(HTTPException) as e:
        ctx["routes"].create_draft(
            ctx["a"],
            DraftCreate(recipient_method_ids=[m1, m2], body="Hello there."),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    assert e.value.status_code == 422
    assert "SEPARATE" in e.value.detail


def test_unverified_recipient_blocks_preview_and_send(ctx):
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    db = ctx["db"]
    # Revoke verification after drafting.
    db.query(ctx["models"].ContactMethod).filter_by(id=mid).update({"verified_at": None})
    db.commit()
    d = _draft(ctx, mid, body="Hello there.")
    with pytest.raises(HTTPException) as e:
        ctx["routes"].preview_draft(ctx["a"], d.id, db=db, _=ctx["admin"])
    assert e.value.status_code == 422


# --- MIME budget (MAIL-02) ------------------------------------------------------


def test_mail02_oversize_image_converts_to_link(ctx):
    """An image over the encoded cap becomes a LINK, never silently dropped."""
    big = _media(ctx, kind="photo", size=12 * 1024 * 1024, name="big.jpg")
    plan = (
        ctx["routes"].plan_attachments([big])
        if hasattr(ctx["routes"], "plan_attachments")
        else None
    )
    from email_center import plan_attachments

    plan = plan_attachments([big])
    assert plan[0]["decision"] == "link"
    assert "cap" in plan[0]["reason"]


def test_video_always_becomes_share_link(ctx):
    from email_center import plan_attachments

    vid = _media(ctx, kind="video", size=100_000, name="clip.mp4")
    plan = plan_attachments([vid])
    assert plan[0]["decision"] == "link"


# --- Send gates -----------------------------------------------------------------


def test_mail01_send_without_confirm_rejected(ctx):
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    d = _draft(ctx, mid, body="Hello there.")
    from schemas import SendRequest

    with pytest.raises(HTTPException) as e:
        ctx["routes"].send_draft(
            ctx["a"],
            d.id,
            SendRequest(confirm=False),
            request=type("R", (), {"base_url": "http://localhost/"})(),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    assert e.value.status_code == 400


def test_send_happy_path_console_honest_status(ctx):
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    obj = _objective(ctx)
    photo = _media(ctx, kind="photo", size=200_000, name="blocks.jpg")
    video = _media(ctx, kind="video", size=3_000_000, name="first-steps.mp4")
    d = _draft(ctx, mid, media_ids=[photo.id, video.id], fact_ids=[obj.id])
    from schemas import SendRequest

    resp = ctx["routes"].send_draft(
        ctx["a"],
        d.id,
        SendRequest(confirm=True),
        request=type("R", (), {"base_url": "http://localhost/"})(),
        db=ctx["db"],
        current_user=ctx["admin"],
    )
    assert len(resp.messages) == 1
    m = resp.messages[0]
    assert m["transport"] == "console" and m["status"] == "logged"
    # Video became a share link in the frozen snapshot; photo attached.
    db = ctx["db"]
    row = db.query(ctx["models"].Message).filter_by(id=m["id"]).first()
    snap = json.loads(row.content_snapshot)
    assert len(snap["attachments"]) == 1
    assert snap["attachments"][0]["name"] == "blocks.jpg"
    assert len(snap["share_links"]) == 1
    assert "/share/" in list(snap["share_links"].values())[0]
    assert "first-steps.mp4" in snap["text_body"]
    # Outbox job done; draft marked sent.
    job = db.query(ctx["models"].OutboxJob).filter_by(message_id=m["id"]).first()
    assert job.state == "done"
    assert db.query(ctx["models"].MessageDraft).filter_by(id=d.id).first().status == "sent"


def test_mail03_retry_does_not_duplicate(ctx):
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    d = _draft(ctx, mid, body="Hello there.")
    from schemas import SendRequest

    req = SendRequest(confirm=True)
    fake_req = type("R", (), {"base_url": "http://localhost/"})()
    ctx["routes"].send_draft(
        ctx["a"], d.id, req, request=fake_req, db=ctx["db"], current_user=ctx["admin"]
    )
    # A second attempt (e.g. client retry after timeout) must NOT re-send.
    with pytest.raises(HTTPException) as e:
        ctx["routes"].send_draft(
            ctx["a"], d.id, req, request=fake_req, db=ctx["db"], current_user=ctx["admin"]
        )
    assert e.value.status_code == 409
    assert ctx["db"].query(ctx["models"].Message).count() == 1


def test_sent_history_is_immutable_snapshot(ctx):
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    d = _draft(ctx, mid, body="Hello there.")
    from schemas import SendRequest

    ctx["routes"].send_draft(
        ctx["a"],
        d.id,
        SendRequest(confirm=True),
        request=type("R", (), {"base_url": "http://localhost/"})(),
        db=ctx["db"],
        current_user=ctx["admin"],
    )
    history = ctx["routes"].list_messages(ctx["a"], db=ctx["db"])
    assert len(history) == 1 and history[0]["subject"]
    # Editing a sent draft is forbidden (audit trail).
    from schemas import DraftUpdate

    with pytest.raises(HTTPException) as e:
        ctx["routes"].update_draft(
            ctx["a"], d.id, DraftUpdate(body="x"), db=ctx["db"], _=ctx["admin"]
        )
    assert e.value.status_code == 409


# --- Authorization gates ---------------------------------------------------------


def test_readonly_and_child_cannot_compose_or_send(ctx):
    """Compose/send is admin-only. The guard is a ROUTER dependency (the repo
    tests call route functions directly, bypassing deps), so assert the wiring:
    require_admin must be attached to the email router."""

    deps = [getattr(d.dependency, "__name__", "") for d in ctx["routes"].router.dependencies]
    assert "require_admin" in deps
    assert "require_profile_access" in deps


def test_cross_profile_media_and_recipients_denied(ctx):
    """Media from Child B cannot be attached to Child A's draft; a contact
    linked only to B cannot receive A's draft."""
    db = ctx["db"]
    other_media = ctx["models"].ProfileMedia(
        profile_id=ctx["b"],
        storage_key="kx.jpg",
        original_name="x.jpg",
        mime_type="image/jpeg",
        media_type="photo",
        size_bytes=10,
        status="ready",
    )
    db.add(other_media)
    db.commit()
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    from schemas import DraftCreate

    with pytest.raises(HTTPException):
        ctx["routes"].create_draft(
            ctx["a"],
            DraftCreate(recipient_method_ids=[mid], media_ids=[other_media.id], body="Hi."),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    # Contact linked to A only: creating a draft under B must 404.
    with pytest.raises(HTTPException) as e:
        ctx["routes"].create_draft(
            ctx["b"],
            DraftCreate(recipient_method_ids=[mid], body="Hi."),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    assert e.value.status_code == 404


# --- Bedrock AI drafts (Pass 5b) --------------------------------------------------


def test_ai_draft_disabled_is_503(ctx, monkeypatch):
    monkeypatch.setenv("BEDROCK_DRAFT_ENABLED", "0")
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    from schemas import AIDraftRequest

    with pytest.raises(HTTPException) as e:
        ctx["routes"].ai_draft(
            ctx["a"],
            AIDraftRequest(recipient_method_ids=[mid]),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    assert e.value.status_code == 503


def test_ai_draft_creates_draft_never_auto_sends(ctx, monkeypatch):
    monkeypatch.setenv("BEDROCK_DRAFT_ENABLED", "1")
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    obj = _objective(ctx)

    class FakeClient:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": json.dumps(
                                    {
                                        "subject": "An update on Robert",
                                        "body": "Robert stacked three blocks today and grinned the whole time.",
                                    }
                                )
                            }
                        ]
                    }
                }
            }

    monkeypatch.setattr(
        ctx["routes"],
        "_bedrock_converse",
        lambda prompt, system: json.dumps(
            {
                "subject": "An update on Robert",
                "body": "Robert stacked three blocks today and grinned the whole time.",
            }
        ),
    )
    from schemas import AIDraftRequest

    d = ctx["routes"].ai_draft(
        ctx["a"],
        AIDraftRequest(recipient_method_ids=[mid], fact_ids=[obj.id]),
        db=ctx["db"],
        current_user=ctx["admin"],
    )
    assert d.status == "draft"  # human approval required; never auto-sent
    assert d.template_key == "bedrock_assisted"
    assert ctx["db"].query(ctx["models"].Message).count() == 0


def test_ai_draft_clinical_leak_rejected(ctx, monkeypatch):
    monkeypatch.setenv("BEDROCK_DRAFT_ENABLED", "1")
    c = _family_contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    monkeypatch.setattr(
        ctx["routes"],
        "_bedrock_converse",
        lambda prompt, system: json.dumps(
            {
                "subject": "Robert",
                "body": "Robert started speech therapy twice weekly for his diagnosis.",
            }
        ),
    )
    from schemas import AIDraftRequest

    with pytest.raises(HTTPException) as e:
        ctx["routes"].ai_draft(
            ctx["a"],
            AIDraftRequest(recipient_method_ids=[mid]),
            db=ctx["db"],
            current_user=ctx["admin"],
        )
    assert e.value.status_code == 422
    assert "disclosure policy" in e.value.detail
