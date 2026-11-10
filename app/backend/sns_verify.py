"""AWS SNS message signature verification (for SES event ingestion).

SNS signs every notification (SignatureVersion 1 = SHA1withRSA over a
type-specific string-to-sign, base64-encoded, signing cert published over
HTTPS). This module verifies that signature BEFORE any event is trusted, and
confirms subscriptions by fetching the SubscribeURL.

Security rules enforced here:
  * The signing-cert URL must be HTTPS on an SNS host allowlist
    (sns.amazonaws.com and regional sns.<region>.amazonaws.com). Never fetch
    from an attacker-controlled host.
  * Signature must verify against the cert's public key; any mismatch,
    missing field, or wrong SignatureVersion is rejected.
  * SubscribeURL confirmation fetches are restricted to the same allowlist.

No third-party HTTP client: stdlib urllib with strict https + allowlist.
"""

from __future__ import annotations

import base64
import re
from urllib import request as _urlreq
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# SNS hosts allowed to serve signing certs / subscription confirmation URLs.
_SNS_HOST_RE = re.compile(r"^sns(\.[a-z0-9-]+)*\.amazonaws\.com$")

# String-to-sign field order per SNS docs, by message Type.
_STRING_TO_SIGN_FIELDS = {
    "Notification": ["Message", "MessageId", "Timestamp", "TopicArn", "Type"],
    "SubscriptionConfirmation": [
        "Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type",
    ],
    "UnsubscribeConfirmation": [
        "Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type",
    ],
}


class SnsVerificationError(ValueError):
    """The SNS message failed signature or allowlist validation."""


def _host_allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return bool(_SNS_HOST_RE.match(host)) and url.lower().startswith("https://")


def _fetch(url: str, timeout: int = 10) -> bytes:
    """Fetch bytes from an allowlisted HTTPS URL (cert or SubscribeURL)."""
    if not _host_allowed(url):
        raise SnsVerificationError(f"URL host is not an allowed SNS endpoint: {url}")
    with _urlreq.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - allowlisted https
        return resp.read()


def _load_public_key(cert_pem_or_der: bytes):
    """Parse a signing cert (PEM or DER) and return its public key."""
    try:
        cert = x509.load_pem_x509_certificate(cert_pem_or_der)
    except ValueError:
        cert = x509.load_der_x509_certificate(cert_pem_or_der)
    return cert.public_key()


def _string_to_sign(payload: dict) -> str:
    msg_type = payload.get("Type", "")
    fields = _STRING_TO_SIGN_FIELDS.get(msg_type)
    if not fields:
        raise SnsVerificationError(f"Unsupported SNS message Type: {msg_type!r}")
    if str(payload.get("SignatureVersion", "1")) != "1":
        raise SnsVerificationError("Only SignatureVersion 1 is supported")
    parts = []
    for field in fields:
        value = payload.get(field)
        if value is None:
            raise SnsVerificationError(f"Missing SNS field for signing: {field}")
        parts.append(f"{field}\n{value}\n")
    return "".join(parts)


def verify_sns_signature(payload: dict, cert_fetch=None) -> None:
    """Verify an SNS message's signature in-place. Raises SnsVerificationError
    on any failure. `cert_fetch` is injectable for tests."""
    cert_url = payload.get("SigningCertURL", "")
    signature = payload.get("Signature", "")
    if not cert_url or not signature:
        raise SnsVerificationError("Missing Signature or SigningCertURL")
    if not _host_allowed(cert_url):
        raise SnsVerificationError("SigningCertURL host is not an allowed SNS endpoint")
    fetch = cert_fetch or _fetch
    public_key = _load_public_key(fetch(cert_url))
    message = _string_to_sign(payload).encode()
    try:
        public_key.verify(
            base64.b64decode(signature),
            message,
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
    except Exception as e:  # noqa: BLE001 - any crypto failure means reject
        raise SnsVerificationError("SNS signature verification failed") from e


def confirm_subscription(subscribe_url: str, url_fetch=None) -> int:
    """Visit the SubscribeURL to confirm an SNS subscription. Returns 200 on
    success (any fetch error propagates). The URL must pass the same allowlist
    as signing certs."""
    fetch = url_fetch or _fetch
    if not _host_allowed(subscribe_url):
        raise SnsVerificationError("SubscribeURL host is not an allowed SNS endpoint")
    fetch(subscribe_url)  # noqa: S310 - allowlisted https; errors propagate
    return 200
