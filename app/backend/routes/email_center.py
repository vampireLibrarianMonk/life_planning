"""Email Center routes (v6 Pass 5) - compose/preview/send via the disclosure
policy in email_center.py. ALL routes are admin-only (parents compose; the
child and readonly roles can never compose or send). Sends go through
notify.get_email_sender(): console backend logs honestly in dev; SES only when
provisioned. Nothing fabricates delivery status."""

import hashlib
import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from auth import require_admin, require_profile_access
from database import get_db
from email_center import (
    DisclosureViolation,
    assert_single_audience,
    audience_for_roles,
    content_snapshot,
    media_bullet,
    plan_attachments,
    recipient_snapshot,
    render_html_body,
    render_text_body,
    template_subject,
    total_encoded_bytes,
    validate_disclosure,
)
from models import (
    Contact,
    ContactMethod,
    MediaShareGrant,
    Message,
    MessageDraft,
    OutboxJob,
    PillarEntry,
    Profile,
    ProfileContactLink,
    ProfileMedia,
    User,
)
from schemas import (
    AIDraftRequest,
    DraftCreate,
    DraftResponse,
    DraftUpdate,
    PreviewResponse,
    SendRequest,
    SendResponse,
)
from storage import get_storage

router = APIRouter(
    prefix="/api/profiles/{profile_id}/email",
    tags=["email"],
    dependencies=[Depends(require_profile_access), Depends(require_admin)],
)

SHARE_GRANT_HOURS = 168  # 7 days for email share links


def _json_list(raw: str) -> list:
    try:
        val = json.loads(raw or "[]")
        return val if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []


def _draft_response(db: Session, d: MessageDraft) -> DraftResponse:
    # Built explicitly: the ORM columns hold JSON strings; from_attributes
    # would try to validate them raw against list[int] and explode.
    return DraftResponse(
        id=d.id,
        profile_id=d.profile_id,
        channel=d.channel,
        audience=d.audience,
        subject=d.subject,
        body=d.body,
        template_key=d.template_key,
        include_clinical=d.include_clinical,
        status=d.status,
        created_at=d.created_at,
        updated_at=d.updated_at,
        recipient_method_ids=_json_list(d.recipient_method_ids),
        selected_media_ids=_json_list(d.selected_media_ids),
    )


def _private_notes(db: Session, profile_id: int) -> list[str]:
    """The profile's PRIVATE worries notes - used only to REJECT leaks; they
    are never returned to the composer (PRIV-04)."""
    rows = (
        db.query(PillarEntry)
        .filter(
            PillarEntry.profile_id == profile_id,
            PillarEntry.category == "child_development_private",
        )
        .all()
    )
    return [r.content or "" for r in rows if (r.content or "").strip()]


def _load_media(db: Session, profile_id: int, media_ids: list[int]) -> list:
    if not media_ids:
        return []
    rows = (
        db.query(ProfileMedia)
        .filter(
            ProfileMedia.id.in_(media_ids),
            ProfileMedia.profile_id == profile_id,  # cross-profile guard
            ProfileMedia.deleted_at.is_(None),
            ProfileMedia.status == "ready",
        )
        .all()
    )
    by_id = {m.id: m for m in rows}
    return [by_id[i] for i in media_ids if i in by_id]


def _resolve_recipients(db: Session, profile_id: int, method_ids: list[int]):
    """Resolve contact methods for the composer. Every method must belong to a
    contact LINKED to this profile (the link is the authorization anchor)."""
    if not method_ids:
        raise HTTPException(status_code=422, detail="Select at least one recipient.")
    methods = (
        db.query(ContactMethod)
        .filter(ContactMethod.id.in_(method_ids), ContactMethod.channel == "email")
        .all()
    )
    found: dict[int, ContactMethod] = {m.id: m for m in methods}
    missing = [i for i in method_ids if i not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"Recipient method(s) not found: {missing}")
    out = []
    for mid in method_ids:
        m = found[mid]
        link = (
            db.query(ProfileContactLink)
            .filter(
                ProfileContactLink.contact_id == m.contact_id,
                ProfileContactLink.profile_id == profile_id,  # cross-profile guard
                ProfileContactLink.active == 1,
            )
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=404,
                detail="A selected recipient is not linked to this profile.",
            )
        contact = db.query(Contact).filter(Contact.id == m.contact_id).first()
        out.append((m, contact, link))
    return out


def _validate_draft_state(db: Session, profile_id: int, d: MessageDraft, recipients):
    """Shared validation for preview + send: one audience, policy, verification."""
    classes = [audience_for_roles(link.roles) for _, _, link in recipients]
    effective = assert_single_audience(classes)
    if effective != d.audience:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Draft audience '{d.audience}' does not match the selected "
                f"recipients ('{effective}'). Recompose as separate drafts."
            ),
        )
    unverified = [
        contact.display_name if contact else m.address
        for m, contact, _ in recipients
        if m.verified_at is None or not m.active
    ]
    if unverified:
        raise HTTPException(
            status_code=422,
            detail="These recipients are not verified yet: " + ", ".join(unverified),
        )
    # Suppression: a bounce/complaint (or explicit opt-out) permanently blocks
    # further sends to that address until the owner clears it (5.5).
    suppressed = [
        contact.display_name if contact else m.address
        for m, contact, _ in recipients
        if m.opted_out_at is not None
    ]
    if suppressed:
        raise HTTPException(
            status_code=422,
            detail=(
                "These recipients are suppressed after a bounce/complaint or "
                "opt-out: " + ", ".join(suppressed)
            ),
        )
    try:
        validate_disclosure(
            d.audience,
            bool(d.include_clinical),
            d.body or "",
            subject=d.subject or "",
            private_notes=_private_notes(db, profile_id),
        )
    except DisclosureViolation as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return effective


def _render_final(d: MessageDraft, plan: list[dict], share_links: dict[int, str], sender_name: str):
    """The EXACT final content: draft body + the media section from the plan."""
    media_lines = [media_bullet(p, share_links.get(p["media_id"])) for p in plan]
    text = render_text_body(
        d.audience, _first_name(d), [], [], [], [], sender_name
    )
    # The stored body already carries facts + note; append media lines only.
    text = (d.body or "").rstrip() + "\n\nPhotos and videos:\n" + "\n".join(
        f"  - {ml}" for ml in media_lines
    ) if media_lines else (d.body or "")
    html_body = _body_to_html(d.body or "")
    if media_lines:
        lis = "".join(
            f"<li>{media_bullet(p, share_links.get(p['media_id']))}</li>" for p in plan
        )
        html_body = html_body.replace(
            "</div>",
            f"<h3 style=\"margin:16px 0 6px;font-size:15px;\">Photos and videos</h3>"
            f"<ul style=\"margin:0;padding-left:20px;\">{lis}</ul></div>",
        )
    return text, html_body


def _first_name(d: MessageDraft) -> str:
    prof = d.profile
    return (prof.name.split(" ")[0] if prof and prof.name else "") or "your child"


def _body_to_html(body: str) -> str:
    """Escape + paragraph-wrap an arbitrary (parent/AI) body. Links auto-linked."""
    import html as _html

    paras = [p.strip() for p in (body or "").split("\n\n") if p.strip()]
    rendered = []
    for p in paras:
        lines = [_html.escape(ln) for ln in p.split("\n")]
        rendered.append("<br>".join(_inline_links(ln) for ln in lines))
    inner = "".join(f"<p style=\"margin:0 0 10px;\">{r}</p>" for r in rendered)
    return (
        "<div style=\"font-family:Arial,Helvetica,sans-serif;font-size:14px;"
        "line-height:1.6;color:#1a1a1a;max-width:640px;\">" + inner + "</div>"
    )


def _inline_links(escaped_text: str):
    from email_center import _inline_links as fn

    return fn(escaped_text)


# --- Composer inputs: facts + recipients --------------------------------------


@router.get("/facts")
def list_facts(profile_id: int, db: Session = Depends(get_db)):
    """The composer's selectable fact sheet. PRIVATE worries are structurally
    EXCLUDED (PRIV-04) - they are never surfaced here, only used to reject."""
    import os

    cd = (
        db.query(PillarEntry)
        .filter(
            PillarEntry.profile_id == profile_id,
            PillarEntry.category.like("child_development%"),
            PillarEntry.category != "child_development_private",
        )
        .order_by(PillarEntry.age_years.asc(), PillarEntry.id.asc())
        .all()
    )
    events = (
        db.query(PillarEntry)
        .filter(PillarEntry.profile_id == profile_id, PillarEntry.entry_type == "event")
        .order_by(PillarEntry.created_at.desc())
        .limit(10)
        .all()
    )
    media = (
        db.query(ProfileMedia)
        .filter(
            ProfileMedia.profile_id == profile_id,
            ProfileMedia.deleted_at.is_(None),
            ProfileMedia.status == "ready",
        )
        .order_by(ProfileMedia.created_at.desc())
        .all()
    )
    return {
        "highlights": [
            {
                "id": e.id,
                "title": e.title,
                "status": e.status,
                "age_band": e.age_band,
                "category": e.category,
                "content": (e.content or "")[:300],
            }
            for e in cd
        ],
        "recent_events": [
            {"id": e.id, "title": e.title, "content": (e.content or "")[:300]} for e in events
        ],
        "media": [
            {
                "id": m.id,
                "name": m.original_name,
                "media_type": m.media_type,
                "mime_type": m.mime_type,
                "size_bytes": m.size_bytes,
                "observation": m.observation,
            }
            for m in media
        ],
        "private_worries_included": False,
        "bedrock_enabled": os.getenv("BEDROCK_DRAFT_ENABLED", "0") == "1",
        "email_backend": os.getenv("NOTIFY_EMAIL_BACKEND", "console"),
    }


@router.get("/recipients")
def list_recipients(profile_id: int, db: Session = Depends(get_db)):
    """Linked contacts + their verified email methods, with the audience class
    the disclosure policy will assign."""
    links = (
        db.query(ProfileContactLink)
        .filter(ProfileContactLink.profile_id == profile_id, ProfileContactLink.active == 1)
        .all()
    )
    out = []
    for link in links:
        contact = db.query(Contact).filter(Contact.id == link.contact_id).first()
        if not contact:
            continue
        for m in contact.methods:
            if m.channel != "email" or not m.active:
                continue
            out.append(
                {
                    "method_id": m.id,
                    "contact_id": contact.id,
                    "display_name": contact.display_name,
                    "address": m.address,
                    "verified": m.verified_at is not None,
                    "roles": link.roles,
                    "audience": audience_for_roles(link.roles),
                    "default_disclosure": link.default_disclosure,
                }
            )
    return out


# --- Drafts --------------------------------------------------------------------


@router.post("/drafts", response_model=DraftResponse, status_code=201)
def create_draft(
    profile_id: int,
    req: DraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    recipients = _resolve_recipients(db, profile_id, req.recipient_method_ids)
    classes = [audience_for_roles(link.roles) for _, _, link in recipients]
    try:
        audience = assert_single_audience(classes)
    except DisclosureViolation as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if req.audience and req.audience != audience:
        raise HTTPException(
            status_code=422,
            detail=f"Selected recipients are audience '{audience}', not '{req.audience}'.",
        )
    # Validate media NOW (cross-profile / deleted / pending ids are rejected at
    # compose time, not silently dropped at send).
    media_rows = _load_media(db, profile_id, req.media_ids)
    if len(media_rows) != len(set(req.media_ids)):
        raise HTTPException(
            status_code=404,
            detail="One or more selected media items were not found on this profile.",
        )
    subject = req.subject or template_subject(audience, _profile_first_name(db, profile_id))
    body = req.body if req.body is not None else _template_body(
        db, profile_id, audience, req.fact_ids, req.note, bool(req.include_clinical)
    )
    d = MessageDraft(
        profile_id=profile_id,
        channel="email",
        author_id=current_user.id,
        audience=audience,
        recipient_method_ids=json.dumps(req.recipient_method_ids),
        subject=subject[:300],
        body=body,
        selected_media_ids=json.dumps(req.media_ids),
        template_key=req.template_key,
        include_clinical=1 if req.include_clinical else 0,
    )
    try:
        validate_disclosure(
            audience, bool(req.include_clinical), body, subject=subject,
            private_notes=_private_notes(db, profile_id),
        )
    except DisclosureViolation as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    db.add(d)
    db.commit()
    db.refresh(d)
    return _draft_response(db, d)


def _profile_first_name(db: Session, profile_id: int) -> str:
    prof = db.query(Profile).filter(Profile.id == profile_id).first()
    return (prof.name.split(" ")[0] if prof and prof.name else "") or "your child"


def _template_body(
    db: Session, profile_id: int, audience: str, fact_ids: list[int],
    note: str | None, include_clinical: bool,
) -> str:
    """Deterministic template: selected facts -> bullets (+ parent note)."""
    facts = []
    if fact_ids:
        rows = (
            db.query(PillarEntry)
            .filter(
                PillarEntry.id.in_(fact_ids),
                PillarEntry.profile_id == profile_id,  # cross-profile guard
            )
            .all()
        )
        by_id = {r.id: r for r in rows}
        for fid in fact_ids:
            e = by_id.get(fid)
            if not e:
                continue
            if (e.category or "") == "child_development_private":
                continue  # never auto-include private worries (PRIV-04)
            is_clinical = bool(e.category and e.category.startswith("clinical"))
            if is_clinical and not (include_clinical and audience == "clinician"):
                continue
            status = f" [{e.status.replace('_', ' ')}]" if e.status else ""
            line = f"{e.title}{status}"
            if e.content:
                line += f" - {e.content[:200]}"
            facts.append(line)
    sections = [f"Hello,", "", f"An update on our child:", ""]
    if facts:
        sections.append("Highlights:")
        sections += [f"  - {f}" for f in facts]
        sections.append("")
    if note:
        sections += [note.strip(), ""]
    sections.append("- Family")
    return "\n".join(sections)


@router.get("/drafts", response_model=list[DraftResponse])
def list_drafts(profile_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(MessageDraft)
        .filter(MessageDraft.profile_id == profile_id)
        .order_by(MessageDraft.updated_at.desc(), MessageDraft.id.desc())
        .all()
    )
    return [_draft_response(db, d) for d in rows]


@router.get("/drafts/{draft_id}", response_model=DraftResponse)
def get_draft(profile_id: int, draft_id: int, db: Session = Depends(get_db)):
    return _draft_response(db, _draft_or_404(db, profile_id, draft_id))


def _draft_or_404(db: Session, profile_id: int, draft_id: int) -> MessageDraft:
    d = (
        db.query(MessageDraft)
        .filter(MessageDraft.id == draft_id, MessageDraft.profile_id == profile_id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    return d


@router.patch("/drafts/{draft_id}", response_model=DraftResponse)
def update_draft(
    profile_id: int,
    draft_id: int,
    req: DraftUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    d = _draft_or_404(db, profile_id, draft_id)
    if d.status == "sent":
        raise HTTPException(status_code=409, detail="Draft already sent.")
    data = req.model_dump(exclude_unset=True)
    if "recipient_method_ids" in data and data["recipient_method_ids"] is not None:
        recipients = _resolve_recipients(db, profile_id, data["recipient_method_ids"])
        classes = [audience_for_roles(link.roles) for _, _, link in recipients]
        data["audience"] = assert_single_audience(classes)
        d.recipient_method_ids = json.dumps(data["recipient_method_ids"])
    if "media_ids" in data and data["media_ids"] is not None:
        d.selected_media_ids = json.dumps(data["media_ids"])
    for field in ("subject", "body", "template_key"):
        if field in data and data[field] is not None:
            setattr(d, field, data[field])
    if "include_clinical" in data and data["include_clinical"] is not None:
        d.include_clinical = 1 if data["include_clinical"] else 0
    try:
        validate_disclosure(
            d.audience, bool(d.include_clinical), d.body or "", subject=d.subject or "",
            private_notes=_private_notes(db, profile_id),
        )
    except DisclosureViolation as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    db.commit()
    db.refresh(d)
    return _draft_response(db, d)


@router.delete("/drafts/{draft_id}", status_code=204)
def delete_draft(
    profile_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    d = _draft_or_404(db, profile_id, draft_id)
    if d.status == "sent":
        raise HTTPException(status_code=409, detail="Sent drafts are part of the audit trail.")
    db.delete(d)
    db.commit()


# --- Preview (exact final, side-effect free) -----------------------------------


@router.post("/drafts/{draft_id}/preview", response_model=PreviewResponse)
def preview_draft(
    profile_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    d = _draft_or_404(db, profile_id, draft_id)
    recipients = _resolve_recipients(db, profile_id, _json_list(d.recipient_method_ids))
    _validate_draft_state(db, profile_id, d, recipients)
    media = _load_media(db, profile_id, _json_list(d.selected_media_ids))
    plan = plan_attachments(media)
    # Preview renders the honest final EXCEPT the opaque token values, which
    # only exist at send (they are random, single-use secrets).
    share_links = {p["media_id"]: None for p in plan if p["decision"] == "link"}
    text, html_body = _render_final(d, plan, share_links, "Family")
    return PreviewResponse(
        draft_id=d.id,
        audience=d.audience,
        recipients=[
            {
                "contact_id": c.id if c else None,
                "display_name": c.display_name if c else m.address,
                "address": m.address,
                "verified": m.verified_at is not None,
            }
            for m, c, _ in recipients
        ],
        subject=d.subject or "",
        text_body=text,
        html_body=html_body,
        attachments=[p for p in plan if p["decision"] == "attach"],
        share_links=[
            {"media_id": p["media_id"], "name": p["name"], "reason": p["reason"]}
            for p in plan
            if p["decision"] == "link"
        ],
        total_encoded_bytes=total_encoded_bytes(plan),
        mime_cap_bytes=10 * 1024 * 1024,
    )


# --- Send (explicit confirm; per-recipient; idempotent) -------------------------


@router.post("/drafts/{draft_id}/send", response_model=SendResponse)
def send_draft(
    profile_id: int,
    draft_id: int,
    req: SendRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    d = _draft_or_404(db, profile_id, draft_id)
    if d.status == "sent":
        raise HTTPException(status_code=409, detail="Draft already sent.")
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Sending requires explicit confirmation (confirm: true).",
        )
    recipients = _resolve_recipients(db, profile_id, _json_list(d.recipient_method_ids))
    _validate_draft_state(db, profile_id, d, recipients)
    # Daily send cap (SES cost/rate guard): count today's dispatched messages
    # account-wide. EMAIL_DAILY_SEND_CAP=0 disables the cap.
    import os

    cap = int(os.getenv("EMAIL_DAILY_SEND_CAP", "200"))
    if cap > 0:
        from datetime import timedelta

        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = (
            db.query(Message)
            .filter(
                Message.sent_at >= day_start,
                Message.sent_at < day_start + timedelta(days=1),
                Message.status.in_(["submitted", "logged", "delivered"]),
            )
            .count()
        )
        if sent_today + len(recipients) > cap:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily email send cap reached ({sent_today} sent today, cap {cap}). "
                    "Try again tomorrow or raise EMAIL_DAILY_SEND_CAP."
                ),
            )
    media = _load_media(db, profile_id, _json_list(d.selected_media_ids))
    plan = plan_attachments(media)

    # Share grants for link-decision media (one per media per send; revocable).
    base = str(request.base_url).rstrip("/")
    share_links: dict[int, str] = {}
    for p in plan:
        if p["decision"] != "link":
            continue
        raw = secrets.token_urlsafe(32)
        grant = MediaShareGrant(
            profile_id=profile_id,
            media_id=p["media_id"],
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(hours=SHARE_GRANT_HOURS),
            created_by=current_user.id,
        )
        db.add(grant)
        db.flush()
        share_links[p["media_id"]] = f"{base}/share/{raw}"

    text, html_body = _render_final(d, plan, share_links, "Family")
    snapshot = content_snapshot(d.subject or "", text, html_body, plan, share_links, d.template_key)

    from notify import get_email_sender

    sender = get_email_sender()
    results = []
    for m, contact, link in recipients:
        key = f"email:d{d.id}:m{m.id}"
        existing = db.query(Message).filter(Message.idempotency_key == key).first()
        if existing:
            results.append(existing)  # MAIL-03: retry never duplicates
            continue
        msg = Message(
            profile_id=profile_id,
            draft_id=d.id,
            channel="email",
            sender=getattr(sender, "_from", None) or "console",
            recipient_contact_id=m.contact_id,
            recipient_address=m.address,
            recipient_snapshot=recipient_snapshot(
                m.contact_id, contact.display_name if contact else "", m.address, link.roles
            ),
            content_snapshot=snapshot,
            transport="console",
            idempotency_key=key,
            status="queued",
        )
        db.add(msg)
        db.flush()
        job = OutboxJob(message_id=msg.id, state="pending")
        db.add(job)
        try:
            result = sender.send(m.address, d.subject or "", text)
        except Exception as e:  # noqa: BLE001 - honest failure per recipient
            msg.status = "failed"
            msg.status_updated_at = datetime.utcnow()
            job.state = "failed"
            job.attempts = 1
            job.last_error = str(e)[:500]
            db.commit()
            results.append(msg)
            continue
        msg.transport = result.get("backend", "console")
        msg.provider_id = result.get("provider_id")
        # Console is NOT a provider: 'logged' is honest. SES MessageId = submitted.
        msg.status = "submitted" if result.get("backend") == "ses" else "logged"
        msg.sent_at = datetime.utcnow()
        msg.status_updated_at = msg.sent_at
        job.state = "done"
        job.attempts = 1
        results.append(msg)
    d.status = "sent"
    db.commit()
    for r in results:
        db.refresh(r)
    return SendResponse(
        draft_id=d.id,
        messages=[
            {
                "id": r.id,
                "to": r.recipient_address,
                "transport": r.transport,
                "status": r.status,
                "provider_id": r.provider_id,
            }
            for r in results
        ],
    )


@router.get("/messages")
def list_messages(profile_id: int, db: Session = Depends(get_db)):
    """Sent history: immutable snapshots (outbound only - no inbox, EMAIL-04)."""
    rows = (
        db.query(Message)
        .filter(Message.profile_id == profile_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .all()
    )
    out = []
    for r in rows:
        snap = {}
        try:
            snap = json.loads(r.content_snapshot or "{}")
        except (ValueError, TypeError):
            snap = {}
        out.append(
            {
                "id": r.id,
                "draft_id": r.draft_id,
                "to": r.recipient_address,
                "subject": snap.get("subject", ""),
                "transport": r.transport,
                "status": r.status,
                "provider_id": r.provider_id,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "attachments": snap.get("attachments", []),
                "share_links": snap.get("share_links", {}),
            }
        )
    return out


# --- Bedrock AI draft assembler (Pass 5b, feature-flagged) ----------------------
# The model ONLY receives parent-selected facts (allowed categories) and must
# not invent details. Output becomes a DRAFT - a human previews and explicitly
# sends. It is never auto-sent and clinical/private content is re-validated by
# the same disclosure policy as hand-written drafts.


def _bedrock_converse(prompt: str, system: str) -> str:
    import os

    import boto3

    model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    region = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-east-1"))
    max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "1200"))
    client = boto3.client("bedrock-runtime", region_name=region)
    resp = client.converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.3, "topP": 0.9},
    )
    parts = resp.get("output", {}).get("message", {}).get("content", [])
    return "".join(p.get("text", "") for p in parts)


def _provenance_check(
    subject: str,
    body: str,
    facts_text: str,
    child_last_name: str,
    recipient_names: list[str],
) -> None:
    """Pass 5b provenance gate: the model may only restate what the parent
    selected. Raises DisclosureViolation on:
      * a NUMBER in the output that does not appear in the provided facts/note
        (invented quantities, dates, dosages, percentages);
      * the child's LAST name (we only ever pass the first name);
      * any recipient's or other contact's display name (hallucinated people).
    """
    import re as _re

    combined = f"{subject}\n{body}"
    facts_norm = " ".join((facts_text or "").split())
    for token in _re.findall(r"\d+", combined):
        if token not in facts_norm:
            raise DisclosureViolation(
                f"AI draft mentions the number {token}, which is not in the "
                "selected facts. Provenance check failed."
            )
    last = (child_last_name or "").strip()
    if last and last.lower() in combined.lower():
        raise DisclosureViolation(
            "AI draft includes the child's last name; only the first name may be used."
        )
    for name in recipient_names:
        clean = (name or "").strip()
        if clean and clean.lower() in combined.lower():
            raise DisclosureViolation(
                "AI draft mentions a contact name that was never provided."
            )


@router.post("/drafts/ai-draft", response_model=DraftResponse, status_code=201)
def ai_draft(
    profile_id: int,
    req: AIDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    import os

    if os.getenv("BEDROCK_DRAFT_ENABLED", "0") != "1":
        raise HTTPException(
            status_code=503,
            detail="Bedrock drafting is not enabled (set BEDROCK_DRAFT_ENABLED=1).",
        )
    # Cost cap: count Bedrock-assisted drafts created today (account-wide).
    ai_cap = int(os.getenv("BEDROCK_DAILY_AI_CAP", "25"))
    if ai_cap > 0:
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ai_today = (
            db.query(MessageDraft)
            .filter(
                MessageDraft.template_key == "bedrock_assisted",
                MessageDraft.created_at >= day_start,
            )
            .count()
        )
        if ai_today >= ai_cap:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily Bedrock draft cap reached ({ai_today} today, cap {ai_cap}). "
                    "Try again tomorrow or raise BEDROCK_DAILY_AI_CAP."
                ),
            )
    recipients = _resolve_recipients(db, profile_id, req.recipient_method_ids)
    classes = [audience_for_roles(link.roles) for _, _, link in recipients]
    audience = assert_single_audience(classes)

    # Build the fact sheet from ONLY the selected, allowed facts.
    facts = []
    if req.fact_ids:
        rows = (
            db.query(PillarEntry)
            .filter(PillarEntry.id.in_(req.fact_ids), PillarEntry.profile_id == profile_id)
            .all()
        )
        by_id = {r.id: r for r in rows}
        for fid in req.fact_ids:
            e = by_id.get(fid)
            if not e or (e.category or "") == "child_development_private":
                continue
            is_clinical = bool(e.category and e.category.startswith("clinical"))
            if is_clinical and not (req.include_clinical and audience == "clinician"):
                continue
            facts.append(f"- {e.title} [{(e.status or '').replace('_', ' ')}]: {(e.content or '')[:200]}")
    media = _load_media(db, profile_id, req.media_ids)
    media_lines = [f"- {m.original_name} ({m.media_type})" for m in media]
    child_first = _profile_first_name(db, profile_id)

    system = (
        "You write short, warm, factual update emails for a parent about their "
        "child. STRICT rules: use ONLY the facts provided; never invent details, "
        "dates, names, or medical claims; never include diagnoses, therapy "
        "details, medications, or clinical vocabulary unless explicitly listed "
        "in the clinical notes; never include the child's last name; keep it "
        "under 180 words; output ONLY JSON with keys 'subject' and 'body'."
    )
    audience_note = (
        "This email goes to a CLINICIAN; clinical notes may be included."
        if audience == "clinician" and req.include_clinical
        else "This email goes to a NON-clinical recipient (family/educator); "
        "clinical vocabulary is forbidden."
    )
    prompt = (
        f"Child's first name: {child_first}\n"
        f"Audience: {audience}. {audience_note}\n"
        f"Selected facts:\n" + ("\n".join(facts) if facts else "- (none selected)") + "\n"
        + ("Media to mention:\n" + "\n".join(media_lines) + "\n" if media_lines else "")
        + (f"Parent's note to weave in: {req.note}\n" if req.note else "")
        + "Write the update email now as JSON: {\"subject\": \"...\", \"body\": \"...\"}"
    )
    raw = _bedrock_converse(prompt, system)
    # Lenient JSON extraction (models may wrap in fences).
    txt = raw.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.startswith("json"):
            txt = txt[4:]
    start, end = txt.find("{"), txt.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(status_code=502, detail="Model returned no JSON payload.")
    try:
        parsed = json.loads(txt[start : end + 1])
    except ValueError as e:
        raise HTTPException(status_code=502, detail="Model JSON was unparseable.") from e
    subject = str(parsed.get("subject", ""))[:300]
    body = str(parsed.get("body", ""))
    if not subject or not body.strip():
        raise HTTPException(status_code=502, detail="Model returned an empty draft.")
    # Provenance gate (5b): output may only restate the selected facts.
    prof = db.query(Profile).filter(Profile.id == profile_id).first()
    child_last = prof.name.split(" ", 1)[1] if prof and len(prof.name.split(" ", 1)) > 1 else ""
    facts_text = "\n".join(facts) + ("\n" + req.note if req.note else "")
    try:
        _provenance_check(
            subject,
            body,
            facts_text,
            child_last,
            [c.display_name for _, c, _ in recipients if c],
        )
    except DisclosureViolation as e:
        raise HTTPException(
            status_code=422,
            detail=f"AI draft rejected by the provenance check: {e}",
        ) from e
    try:
        validate_disclosure(
            audience, bool(req.include_clinical), body, subject=subject,
            private_notes=_private_notes(db, profile_id),
        )
    except DisclosureViolation as e:
        raise HTTPException(
            status_code=422,
            detail=f"AI draft rejected by the disclosure policy: {e}",
        ) from e
    d = MessageDraft(
        profile_id=profile_id,
        channel="email",
        author_id=current_user.id,
        audience=audience,
        recipient_method_ids=json.dumps(req.recipient_method_ids),
        subject=subject,
        body=body,
        selected_media_ids=json.dumps(req.media_ids),
        template_key="bedrock_assisted",
        include_clinical=1 if req.include_clinical else 0,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _draft_response(db, d)
