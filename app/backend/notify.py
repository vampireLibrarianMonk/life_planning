"""Notification sender abstraction (email / SMS).

The verification flow is REAL and fully built; what is deliberately pluggable is
the actual delivery. Nothing here fabricates a "sent" status:

  * ConsoleSender (local/dev, default): records the message in-process and logs
    a redacted line so the verification flow is end-to-end testable WITHOUT any
    provider. It never claims a message reached a real inbox/phone.
  * SesSender / SmsSender: real adapters, wired but INERT until their provider
    is provisioned (SES production access / A2P 10DLC). They raise
    SenderNotProvisionedError so a caller can surface an honest "not set up yet"
    rather than silently dropping or faking delivery.

Selection is by env:
  NOTIFY_EMAIL_BACKEND = console | ses     (default: console)
  NOTIFY_SMS_BACKEND   = console | aws     (default: console)
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger("notify")


class SenderNotProvisionedError(RuntimeError):
    """Raised when a real provider backend is selected but not yet configured."""


def _redact(address: str) -> str:
    """Redact a destination for logs (never log full emails/phones)."""
    if "@" in address:
        name, _, domain = address.partition("@")
        return f"{name[:2]}***@{domain}"
    return f"***{address[-4:]}" if len(address) >= 4 else "***"


class Sender(ABC):
    channel: str

    @abstractmethod
    def send(self, to_address: str, subject: str, body: str) -> dict:
        """Deliver a message. Returns a provider-result dict. MUST raise rather
        than fabricate success if it cannot actually send."""
        ...


class ConsoleSender(Sender):
    """Dev/test backend: capture + log (redacted). Not a real delivery."""

    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.sent: list[dict] = []  # in-process record for tests/inspection

    def send(self, to_address: str, subject: str, body: str) -> dict:
        rec = {"channel": self.channel, "to": to_address, "subject": subject, "body": body}
        self.sent.append(rec)
        logger.info(
            "[notify:%s] (console) -> %s subject=%r",
            self.channel,
            _redact(to_address),
            subject,
        )
        return {"backend": "console", "status": "logged", "to": _redact(to_address)}


class SesSender(Sender):
    """Amazon SES v2 email sender. Inert until SES is provisioned + a verified
    sender identity is configured (NOTIFY_EMAIL_FROM)."""

    channel = "email"

    def __init__(self) -> None:
        # Reuse the project's existing proven sender env (SES_SENDER —
        # no-reply@life-planning.my-deployment.com, domain-verified + DKIM
        # aligned), falling back to NOTIFY_EMAIL_FROM for flexibility.
        self._from = (os.getenv("SES_SENDER") or os.getenv("NOTIFY_EMAIL_FROM") or "").strip()

    def send(self, to_address: str, subject: str, body: str) -> dict:
        if not self._from:
            raise SenderNotProvisionedError(
                "SES email backend selected but neither SES_SENDER nor "
                "NOTIFY_EMAIL_FROM (a verified SES sender identity) is set. "
                "Email verification is not yet live."
            )
        import boto3  # lazy

        client = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
        kwargs = {}
        # When a configuration set is configured (SES event pipeline), tag the
        # send so bounce/complaint/delivery events flow back to /api/email/events.
        config_set = os.getenv("SES_CONFIG_SET", "").strip()
        if config_set:
            kwargs["ConfigurationSetName"] = config_set
        resp = client.send_email(
            Source=self._from,
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
            **kwargs,
        )
        logger.info("[notify:email] (ses) -> %s id=%s", _redact(to_address), resp.get("MessageId"))
        return {"backend": "ses", "status": "submitted", "provider_id": resp.get("MessageId")}


class SmsSender(Sender):
    """AWS End User Messaging (pinpoint-sms-voice-v2) SMS sender. Inert until an
    origination identity is provisioned (NOTIFY_SMS_ORIGINATION) + A2P 10DLC
    registration/consent are in place."""

    channel = "sms"

    def __init__(self) -> None:
        self._origination = os.getenv("NOTIFY_SMS_ORIGINATION", "").strip()

    def send(self, to_address: str, subject: str, body: str) -> dict:
        if not self._origination:
            raise SenderNotProvisionedError(
                "AWS SMS backend selected but NOTIFY_SMS_ORIGINATION (a registered "
                "10DLC/toll-free origination identity) is not set. SMS verification "
                "is not yet live — A2P 10DLC registration + recipient consent are "
                "launch prerequisites."
            )
        import boto3  # lazy

        client = boto3.client(
            "pinpoint-sms-voice-v2", region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        resp = client.send_text_message(
            DestinationPhoneNumber=to_address,
            OriginationIdentity=self._origination,
            MessageBody=body,
        )
        logger.info("[notify:sms] (aws) -> %s id=%s", _redact(to_address), resp.get("MessageId"))
        return {"backend": "aws", "status": "submitted", "provider_id": resp.get("MessageId")}


# Process-wide senders (console instances are reused so tests can inspect them).
_EMAIL: Sender | None = None
_SMS: Sender | None = None


def get_email_sender() -> Sender:
    global _EMAIL
    if _EMAIL is None:
        backend = os.getenv("NOTIFY_EMAIL_BACKEND", "console").strip().lower()
        _EMAIL = SesSender() if backend == "ses" else ConsoleSender("email")
    return _EMAIL


def get_sms_sender() -> Sender:
    global _SMS
    if _SMS is None:
        backend = os.getenv("NOTIFY_SMS_BACKEND", "console").strip().lower()
        _SMS = SmsSender() if backend == "aws" else ConsoleSender("sms")
    return _SMS


def sender_for(channel: str) -> Sender:
    return get_email_sender() if channel == "email" else get_sms_sender()


def reset_senders() -> None:
    """Test hook: drop cached senders so env changes take effect."""
    global _EMAIL, _SMS
    _EMAIL = None
    _SMS = None
