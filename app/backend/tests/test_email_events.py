"""SES event ingestion (v6 Pass 5.5) + send-cap + Bedrock 5b gates.

Route-function level per repo convention. Covers:
  SNS-01   valid SNS signature accepted; tampered payload rejected
  SNS-02   signing-cert host allowlist enforced
  SNS-03   SubscriptionConfirmation visits the (allowlisted) SubscribeURL
  EVT-01   permanent bounce -> message FAILED + contact method suppressed
  EVT-02   delivery -> message DELIVERED
  EVT-03   complaint -> COMPLAINED + suppressed
  EVT-04   unknown provider id is ignored (no oracle)
  SUP-01   suppressed recipient blocks preview/send
  CAP-01   daily send cap enforced (429)
  AI-05    provenance: invented number rejected; last-name leak rejected
  AI-06    daily Bedrock draft cap enforced (429)
"""

import base64
import datetime
import importlib
import json
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    monkeypatch.setenv("NOTIFY_EMAIL_BACKEND", "console")
    for mod in (
        "config", "database", "models", "auth", "storage", "main",
        "email_center", "notify", "sns_verify",
        "routes.contacts", "routes.gallery", "routes.email_center",
        "routes.email_events",
    ):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    ec = importlib.import_module("routes.email_center")
    ev = importlib.import_module("routes.email_events")
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
    db.add(a)
    db.flush()
    admin = models.User(
        username="admin", hashed_password="x", display_name="A", role=models.Role.admin, id=1
    )
    db.add(admin)
    db.commit()
    return {
        "ec": ec, "ev": ev, "contacts": contacts, "models": models, "storage": storage,
        "notify": notify, "db": db, "a": a.id, "admin": admin,
    }


def _contact(ctx, name="Grandma Sara", addr="grandma@example.com", roles="family"):
    from schemas import ContactCreate, ContactMethodCreate

    return ctx["contacts"].create_contact(
        ctx["a"],
        ContactCreate(
            display_name=name,
            methods=[ContactMethodCreate(channel="email", address=addr)],
            roles=roles,
        ),
        db=ctx["db"],
        current_user=ctx["admin"],
    )


def _verified_method_id(ctx, contact_id):
    db = ctx["db"]
    m = db.query(ctx["models"].ContactMethod).filter_by(contact_id=contact_id).first()
    m.verified_at = datetime.datetime.utcnow()
    db.commit()
    return m.id


def _draft_and_send(ctx, method_id, body="Hello there."):
    from schemas import DraftCreate, SendRequest

    d = ctx["ec"].create_draft(
        ctx["a"],
        DraftCreate(recipient_method_ids=[method_id], body=body),
        db=ctx["db"],
        current_user=ctx["admin"],
    )
    return ctx["ec"].send_draft(
        ctx["a"], d.id, SendRequest(confirm=True),
        request=type("R", (), {"base_url": "http://localhost/"})(),
        db=ctx["db"], current_user=ctx["admin"],
    )


# --- SNS signature helpers ------------------------------------------------------


def _make_key_and_cert():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sns.test.amazonaws.com")])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _signed_sns_payload(key, msg_type, message, subscribe_url=None):
    import sns_verify

    payload = {
        "Type": msg_type,
        "MessageId": "sns-msg-1",
        "TopicArn": "arn:aws:sns:us-east-1:809784555426:life-planning-email-events",
        "Timestamp": "2026-11-10T17:00:00Z",
        "SignatureVersion": "1",
        "SigningCertURL": "https://sns.test.amazonaws.com/cert.pem",
        "Message": message,
    }
    if subscribe_url:
        payload["SubscribeURL"] = subscribe_url
        payload["Token"] = "tok"
    fields = sns_verify._STRING_TO_SIGN_FIELDS[msg_type]
    sts = "".join(f"{f}\n{payload[f]}\n" for f in fields)
    sig = key.sign(sts.encode(), __import__("cryptography").hazmat.primitives.asymmetric.padding.PKCS1v15(), __import__("cryptography").hazmat.primitives.hashes.SHA1())
    payload["Signature"] = base64.b64encode(sig).decode()
    return payload


def _ingest(ctx, payload, monkeypatch, cert_pem, fetch=None):
    """Call the ingestion route with the cert fetcher stubbed to our test cert
    (or a custom fetcher, e.g. one that also serves the SubscribeURL)."""
    import asyncio

    monkeypatch.setattr(
        __import__("sns_verify"), "_fetch", fetch or (lambda url, timeout=10: cert_pem)
    )
    request = type("R", (), {"headers": {}})()

    async def _json():
        return payload

    request.json = _json
    # The route is async; drive it on a fresh loop (no real async I/O inside).
    return asyncio.run(ctx["ev"].ingest_event(request, db=ctx["db"]))


# --- SNS signature gates ---------------------------------------------------------


def test_sns01_valid_signature_accepted_tampered_rejected(ctx, monkeypatch):
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    payload = _signed_sns_payload(
        key, "Notification", json.dumps({"notificationType": "delivery", "mail": {"messageId": "x"}})
    )
    out = _ingest(ctx, payload, monkeypatch, pem)
    assert out["ok"] is True
    # Tamper with the message body -> signature no longer matches.
    payload["Message"] = json.dumps({"notificationType": "bounce", "mail": {"messageId": "x"}})
    with pytest.raises(HTTPException) as e:
        _ingest(ctx, payload, monkeypatch, pem)
    assert e.value.status_code == 403


def test_sns02_cert_host_allowlist_enforced(ctx, monkeypatch):
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    payload = _signed_sns_payload(key, "Notification", "{}")
    payload["SigningCertURL"] = "https://evil.example.com/cert.pem"
    with pytest.raises(HTTPException) as e:
        _ingest(ctx, payload, monkeypatch, pem)
    assert e.value.status_code == 403


def test_sns03_subscription_confirmation_visits_subscribe_url(ctx, monkeypatch):
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    payload = _signed_sns_payload(
        key, "SubscriptionConfirmation", "confirm", subscribe_url="https://sns.test.amazonaws.com/confirm?token=tok"
    )
    visited = []

    def fake_fetch(url, timeout=10):
        # The cert fetch happens first (verification), then the SubscribeURL.
        if "confirm" not in url:
            return pem
        visited.append(url)

        class R:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return b"ok"

    out = _ingest(ctx, payload, monkeypatch, pem, fetch=fake_fetch)
    assert out["ok"] is True and out["action"] == "SubscriptionConfirmation"
    assert visited and "confirm" in visited[0]


# --- Event processing ------------------------------------------------------------


def _sent_message_with_provider(ctx, method_id, provider_id="ses-msg-1"):
    resp = _draft_and_send(ctx, method_id)
    db = ctx["db"]
    msg = db.query(ctx["models"].Message).filter_by(id=resp.messages[0]["id"]).first()
    msg.provider_id = provider_id
    msg.transport = "ses"
    msg.status = "submitted"
    db.commit()
    return msg


def test_evt01_permanent_bounce_fails_and_suppresses(ctx, monkeypatch):
    c = _contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    msg = _sent_message_with_provider(ctx, mid)
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    event = {
        "notificationType": "bounce",
        "bounce": {"bounceType": "Permanent", "messageId": "ses-msg-1"},
        "mail": {"messageId": "ses-msg-1"},
    }
    payload = _signed_sns_payload(key, "Notification", json.dumps(event))
    out = _ingest(ctx, payload, monkeypatch, pem)
    assert out["processed"] == 1
    db = ctx["db"]
    assert db.query(ctx["models"].Message).get(msg.id).status == "failed"
    method = db.query(ctx["models"].ContactMethod).get(mid)
    assert method.opted_out_at is not None
    assert db.query(ctx["models"].MessageEvent).filter_by(message_id=msg.id).count() == 1


def test_evt02_delivery_marks_delivered(ctx, monkeypatch):
    c = _contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    msg = _sent_message_with_provider(ctx, mid)
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    event = {"notificationType": "delivery", "delivery": {"messageId": "ses-msg-1"}}
    payload = _signed_sns_payload(key, "Notification", json.dumps(event))
    _ingest(ctx, payload, monkeypatch, pem)
    assert ctx["db"].query(ctx["models"].Message).get(msg.id).status == "delivered"


def test_evt03_complaint_suppresses(ctx, monkeypatch):
    c = _contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    msg = _sent_message_with_provider(ctx, mid)
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    event = {"notificationType": "complaint", "complaint": {"messageId": "ses-msg-1"}}
    payload = _signed_sns_payload(key, "Notification", json.dumps(event))
    _ingest(ctx, payload, monkeypatch, pem)
    db = ctx["db"]
    assert db.query(ctx["models"].Message).get(msg.id).status == "complained"
    assert db.query(ctx["models"].ContactMethod).get(mid).opted_out_at is not None


def test_evt04_unknown_provider_id_ignored(ctx, monkeypatch):
    key, cert = _make_key_and_cert()
    pem = cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
    event = {"notificationType": "delivery", "delivery": {"messageId": "no-such-id"}}
    payload = _signed_sns_payload(key, "Notification", json.dumps(event))
    out = _ingest(ctx, payload, monkeypatch, pem)
    assert out["processed"] == 0


def test_sup01_suppressed_recipient_blocks_send(ctx, monkeypatch):
    c = _contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    _sent_message_with_provider(ctx, mid)
    db = ctx["db"]
    # Simulate the suppression an event would set.
    db.query(ctx["models"].ContactMethod).filter_by(id=mid).update(
        {"opted_out_at": datetime.datetime.utcnow()}
    )
    db.commit()
    from schemas import DraftCreate

    d = ctx["ec"].create_draft(
        ctx["a"],
        DraftCreate(recipient_method_ids=[mid], body="Hello again."),
        db=db,
        current_user=ctx["admin"],
    )
    with pytest.raises(HTTPException) as e:
        ctx["ec"].preview_draft(ctx["a"], d.id, db=db, _=ctx["admin"])
    assert e.value.status_code == 422
    assert "suppressed" in e.value.detail


def test_cap01_daily_send_cap_enforced(ctx, monkeypatch):
    monkeypatch.setenv("EMAIL_DAILY_SEND_CAP", "1")
    c = _contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    _draft_and_send(ctx, mid)  # first send OK (cap 1)
    from schemas import DraftCreate, SendRequest

    d = ctx["ec"].create_draft(
        ctx["a"],
        DraftCreate(recipient_method_ids=[mid], body="Second."),
        db=ctx["db"],
        current_user=ctx["admin"],
    )
    with pytest.raises(HTTPException) as e:
        ctx["ec"].send_draft(
            ctx["a"], d.id, SendRequest(confirm=True),
            request=type("R", (), {"base_url": "http://localhost/"})(),
            db=ctx["db"], current_user=ctx["admin"],
        )
    assert e.value.status_code == 429


# --- Bedrock 5b: provenance + cost caps -------------------------------------------


def _ai_draft(ctx, monkeypatch, model_output, fact_ids=None):
    monkeypatch.setenv("BEDROCK_DRAFT_ENABLED", "1")
    c = _contact(ctx)
    mid = _verified_method_id(ctx, c.id)
    monkeypatch.setattr(ctx["ec"], "_bedrock_converse", lambda p, s: model_output)
    from schemas import AIDraftRequest

    return ctx["ec"].ai_draft(
        ctx["a"],
        AIDraftRequest(recipient_method_ids=[mid], fact_ids=fact_ids or []),
        db=ctx["db"],
        current_user=ctx["admin"],
    )


def test_ai05_provenance_invented_number_rejected(ctx, monkeypatch):
    obj = ctx["models"].PillarEntry(
        profile_id=ctx["a"], pillar="education", title="Stacks blocks",
        status="complete", category="child_development:motor", is_milestone=1,
    )
    ctx["db"].add(obj)
    ctx["db"].commit()
    output = json.dumps({
        "subject": "Robert",
        "body": "Robert stacked 7 blocks today, a personal best!",
    })
    with pytest.raises(HTTPException) as e:
        _ai_draft(ctx, monkeypatch, output, fact_ids=[obj.id])
    assert e.value.status_code == 422
    assert "provenance" in e.value.detail


def test_ai05_provenance_last_name_leak_rejected(ctx, monkeypatch):
    output = json.dumps({
        "subject": "Robert Test update",
        "body": "Robert Test had a great day.",
    })
    with pytest.raises(HTTPException) as e:
        _ai_draft(ctx, monkeypatch, output)
    assert e.value.status_code == 422
    assert "last name" in e.value.detail


def test_ai05_provenance_clean_output_accepted(ctx, monkeypatch):
    obj = ctx["models"].PillarEntry(
        profile_id=ctx["a"], pillar="education", title="Stacks blocks",
        status="complete", category="child_development:motor", is_milestone=1,
    )
    ctx["db"].add(obj)
    ctx["db"].commit()
    output = json.dumps({
        "subject": "Robert",
        "body": "Robert stacked blocks today and was proud of it.",
    })
    d = _ai_draft(ctx, monkeypatch, output, fact_ids=[obj.id])
    assert d.status == "draft" and d.template_key == "bedrock_assisted"


def test_ai06_daily_bedrock_cap_enforced(ctx, monkeypatch):
    monkeypatch.setenv("BEDROCK_DAILY_AI_CAP", "1")
    output = json.dumps({"subject": "Robert", "body": "A good day."})
    _ai_draft(ctx, monkeypatch, output)
    with pytest.raises(HTTPException) as e:
        _ai_draft(ctx, monkeypatch, output)
    assert e.value.status_code == 429
