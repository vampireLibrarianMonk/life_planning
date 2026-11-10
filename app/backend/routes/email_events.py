"""SES delivery-event ingestion (v6 Pass 5.5).

A PUBLIC endpoint that Amazon SNS calls with SES event notifications
(bounce / complaint / delivery / send). There is no user session here - the
SNS message SIGNATURE is the authentication: every payload is verified via
sns_verify before anything is trusted or recorded.

What it does:
  * SubscriptionConfirmation -> verify, then GET the SubscribeURL (auto-confirm
    so the prod subscription activates as soon as this endpoint is deployed).
  * Notification -> verify, parse the SES event JSON, find the Message by the
    SES MessageId (provider_id), append a MessageEvent row, and update the
    message status truthfully:
        delivery  -> DELIVERED
        bounce (Permanent) -> FAILED + suppress the contact method
        complaint -> COMPLAINED + suppress the contact method
        bounce (Temporary) -> stays SUBMITTED (event recorded only)
    Suppression sets ContactMethod.opted_out_at so future sends refuse the
    address (the composer surfaces this honestly).
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import ContactMethod, Message, MessageEvent
from sns_verify import SnsVerificationError, confirm_subscription, verify_sns_signature

logger = logging.getLogger("email_events")

router = APIRouter(prefix="/api/email", tags=["email-events"])

# Status values used on messages (kept consistent with the send path).
_STATUS_DELIVERED = "delivered"
_STATUS_FAILED = "failed"
_STATUS_COMPLAINED = "complained"


def _ses_message_ids(event: dict) -> list[str]:
    """Extract the SES MessageId(s) an event refers to (usually exactly one)."""
    ids = []
    for key in ("MessageId", "mail", "bounce", "complaint", "delivery"):
        node = event.get(key)
        if key == "mail" and isinstance(node, dict):
            if node.get("messageId"):
                ids.append(node["messageId"])
        elif isinstance(node, dict) and node.get("messageId"):
            ids.append(node["messageId"])
        elif key == "MessageId" and isinstance(node, str):
            ids.append(node)
    # De-duplicate, preserve order.
    seen: set[str] = set()
    out: list[str] = []
    for mid in ids:
        if mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


def _apply_event(db: Session, event: dict, raw: str) -> int:
    """Apply one SES event to matching messages. Returns rows touched."""
    ntype = event.get("notificationType", "")
    ids = _ses_message_ids(event)
    touched = 0
    for mid in ids:
        msg = db.query(Message).filter(Message.provider_id == mid).first()
        if not msg:
            continue  # unknown provider id: record nothing (no oracle)
        suppress = False
        new_status = None
        if ntype == "delivery":
            new_status = _STATUS_DELIVERED
        elif ntype == "bounce":
            bounce_type = (event.get("bounce", {}) or {}).get("bounceType", "")
            if bounce_type == "Permanent":
                new_status = _STATUS_FAILED
                suppress = True
            # Temporary bounces stay submitted; the event is still recorded.
        elif ntype == "complaint":
            new_status = _STATUS_COMPLAINED
            suppress = True
        db.add(
            MessageEvent(
                message_id=msg.id,
                provider_event_id=event.get("eventId") or mid,
                type=ntype.lower() or "unknown",
                raw=raw[:8000],
            )
        )
        if new_status:
            msg.status = new_status
            msg.status_updated_at = datetime.utcnow()
        if suppress and msg.recipient_contact_id:
            method = (
                db.query(ContactMethod)
                .filter(ContactMethod.contact_id == msg.recipient_contact_id)
                .first()
            )
            if method and method.opted_out_at is None:
                method.opted_out_at = datetime.utcnow()
        touched += 1
    db.commit()
    return touched


@router.post("/events")
async def ingest_event(request: Request, db: Session = Depends(get_db)):
    """Receive one SNS message (SES event pipeline). Signature-verified."""
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Body must be JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    try:
        verify_sns_signature(payload)
    except SnsVerificationError as e:
        logger.warning("Rejected SNS message: %s", e)
        raise HTTPException(status_code=403, detail="SNS signature verification failed") from e

    msg_type = payload.get("Type", "")
    if msg_type in ("SubscriptionConfirmation", "UnsubscribeConfirmation"):
        # Auto-confirm by visiting the (allowlisted) SubscribeURL.
        status = confirm_subscription(payload.get("SubscribeURL", ""))
        logger.info("SNS %s confirmed via SubscribeURL (HTTP %s)", msg_type, status)
        return {"ok": True, "action": msg_type, "http_status": status}

    if msg_type != "Notification":
        raise HTTPException(status_code=400, detail=f"Unsupported SNS Type: {msg_type}")

    raw = payload.get("Message", "")
    try:
        event = json.loads(raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="SNS Message is not JSON") from None
    touched = _apply_event(db, event, raw)
    return {"ok": True, "processed": touched}
