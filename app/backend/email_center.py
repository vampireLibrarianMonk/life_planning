"""Email Center core (v6 Pass 5) - disclosure policy, templates, MIME budget.

THE SAFETY CORE. Everything the routes do funnels through this module so the
privacy rules live in exactly one place:

  * AUDIENCE CLASSES: every contact role maps to exactly one audience class
    (family / clinician / educator). A draft serves ONE audience - mixed
    audiences are rejected, never blended.
  * DISCLOSURE POLICY: which categories each audience may receive. Clinical
    content requires an explicit clinician audience + explicit opt-in.
  * PRIVATE WORRIES: child_development_private notes are structurally excluded
    from the composer's fact sheet AND any draft body containing them verbatim
    is rejected (PRIV-04). Not includable in this MVP - even to clinicians.
  * MIME BUDGET: 10 MiB encoded cap (SES hard limit 40 MB). Photos attach only
    if the recomputed running total fits; videos and over-cap images ALWAYS
    become app share links (MAIL-02) - never silently dropped.
  * TEMPLATES: deterministic, HTML-escaped.

Nothing here performs I/O or authorization - routes own that.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime

AUDIENCES = ("family", "clinician", "educator")

# Contact role (CONTACT_ROLES keys) -> audience class. Unknown roles map to
# 'family' (the most restrictive non-clinical class).
ROLE_TO_AUDIENCE: dict[str, str] = {
    "pediatrician": "clinician",
    "speech_therapist": "clinician",
    "occupational_therapist": "clinician",
    "other_clinician": "clinician",
    "educator": "educator",
    "childcare": "educator",
    "caregiver": "family",
    "family": "family",
    "guardian": "family",
    "emergency_contact": "family",
    "other": "family",
}

# Categories a composer may include: highlights / media / schedule / clinical /
# private_worries (the last is NEVER allowed - see validate_disclosure).
DATA_CATEGORIES = ("highlights", "media", "schedule", "clinical", "private_worries")

DISCLOSURE_POLICY: dict[str, frozenset[str]] = {
    "family": frozenset({"highlights", "media", "schedule"}),
    "educator": frozenset({"highlights", "media", "schedule"}),
    "clinician": frozenset({"highlights", "media", "schedule", "clinical"}),
}

# Heuristic clinical-term scanner (defense in depth behind include_clinical).
_CLINICAL_TERM_RE = re.compile(
    r"\b("
    r"diagnos(is|ed|es|e)|disorder|syndrome|pathology|"
    r"therapy|therapist|therapeutic|speech[- ]?therapy|occupational[- ]?therapy|"
    r"IEP|504 plan|medication|medicated|dosage|ssri|stimulant|"
    r"seizure|convulsion|prognosis|symptom(?:s|atic)?|"
    r"autis(?:m|tic)|ADHD|ADD\b|ASD\b|apraxia|dyspraxia|"
    r"evaluation report|clinical|clinician|prescription|referral"
    r")\b",
    re.IGNORECASE,
)


class DisclosureViolation(ValueError):
    """A draft violates the recipient-class disclosure policy."""


def audience_for_roles(roles_csv: str) -> str:
    """Map a contact link's role CSV to its audience class. With multiple roles
    the MOST RESTRICTIVE class wins (family beats clinician)."""
    order = {"family": 0, "educator": 1, "clinician": 2}
    classes = set()
    for raw in (roles_csv or "other").split(","):
        classes.add(ROLE_TO_AUDIENCE.get(raw.strip(), "family"))
    return min(classes, key=lambda c: order[c]) if classes else "family"


def validate_disclosure(
    audience: str,
    include_clinical: bool,
    body: str,
    subject: str = "",
    private_notes: list[str] | None = None,
) -> None:
    """Validate a draft against the disclosure policy. Raises
    DisclosureViolation (routes map it to 422)."""
    if audience not in DISCLOSURE_POLICY:
        raise DisclosureViolation(f"Unknown audience class: {audience}")
    combined = f"{subject}\n{body or ''}"
    if include_clinical and audience != "clinician":
        raise DisclosureViolation(
            "Clinical content requires a clinician audience. Split this into a "
            "separate clinician draft."
        )
    if not include_clinical and audience != "clinician" and _CLINICAL_TERM_RE.search(combined):
        raise DisclosureViolation(
            "This draft looks like it contains clinical/therapy details, which "
            "this recipient class must not receive. Remove them or send a "
            "separate clinician draft."
        )
    for note in private_notes or []:
        snippet = (note or "").strip()
        if snippet and snippet in (body or ""):
            raise DisclosureViolation(
                "Private worries notes must never be included in an email."
            )


def assert_single_audience(audience_classes: list[str]) -> str:
    """Enforce one-audience-per-draft. Returns the single class or raises."""
    unique = sorted(set(audience_classes))
    if not unique:
        raise DisclosureViolation("Select at least one recipient.")
    if len(unique) > 1:
        raise DisclosureViolation(
            "Mixed audiences (" + ", ".join(unique) + ") must be sent as "
            "SEPARATE drafts - never one blended email."
        )
    return unique[0]


# --- MIME budget / attachment planning ---------------------------------------

MAX_ENCODED_TOTAL_BYTES = 10 * 1024 * 1024  # 10 MiB encoded cap (SES limit 40 MB)
BASE64_OVERHEAD = 4 / 3


def encoded_size(raw_bytes: int) -> int:
    return int(raw_bytes * BASE64_OVERHEAD)


def plan_attachments(media_rows: list) -> list[dict]:
    """Decide attach-vs-share-link per selected media item (MAIL-02):
    videos/documents ALWAYS link; photos attach only within the running
    encoded budget; over-cap photos convert to links (never dropped)."""
    plan: list[dict] = []
    running = 0
    for m in media_rows:
        size = int(m.size_bytes or 0)
        enc = encoded_size(size)
        if m.media_type == "video":
            decision, reason = "link", "videos are shared as app links, never attachments"
        elif m.media_type == "document":
            decision, reason = "link", "documents are shared as app links"
        elif running + enc <= MAX_ENCODED_TOTAL_BYTES:
            decision, reason = "attach", "within MIME budget"
            running += enc
        else:
            decision, reason = "link", "over the 10 MiB encoded cap - converted to a link"
        plan.append(
            {
                "media_id": m.id,
                "name": m.original_name,
                "media_type": m.media_type,
                "mime_type": m.mime_type,
                "size_bytes": size,
                "encoded_bytes": enc if decision == "attach" else 0,
                "decision": decision,
                "reason": reason,
            }
        )
    return plan


def total_encoded_bytes(plan: list[dict]) -> int:
    return sum(p["encoded_bytes"] for p in plan)


# --- Deterministic templates ---------------------------------------------------

TEMPLATE_KEYS = {
    "family": "family_update",
    "clinician": "clinician_update",
    "educator": "educator_update",
}


def _fmt_size(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB" if n >= 1024 * 1024 else f"{max(1, n // 1024)} KB"


def template_subject(audience: str, child_first_name: str) -> str:
    """Subjects omit clinical/child-identifying detail beyond the first name."""
    first = html.escape(child_first_name)
    if audience == "clinician":
        return f"{first} - progress update"
    if audience == "educator":
        return f"{first} - home update"
    return f"An update on {first}"


def render_text_body(
    audience: str,
    child_first_name: str,
    highlights: list[str],
    schedule: list[str],
    clinical: list[str],
    media_lines: list[str],
    sender_name: str,
) -> str:
    """Plain-text body. media_lines are pre-rendered bullets."""
    first = child_first_name
    if audience == "clinician":
        opener = f"A quick progress note on {first}:"
    elif audience == "educator":
        opener = f"A short update on {first} from home:"
    else:
        opener = f"Here's what's new with {first}:"
    lines = ["Hello,", "", opener]
    if highlights:
        lines += ["", "Highlights:"] + [f"  - {h}" for h in highlights]
    if clinical and audience == "clinician":
        lines += ["", "Clinical notes:"] + [f"  - {c}" for c in clinical]
    if schedule:
        lines += ["", "Dates to know:"] + [f"  - {s}" for s in schedule]
    if media_lines:
        lines += ["", "Photos and videos:"] + [f"  - {m}" for m in media_lines]
    lines += ["", "- " + (sender_name or "Family")]
    return "\n".join(lines)


def _inline_links(escaped_text: str) -> str:
    """Turn https?:// URLs (already escaped) into anchor tags."""
    return re.sub(
        r"(https?://[^\s<\"]+)",
        r"<a href=\"\1\" rel=\"noopener noreferrer\" target=\"_blank\">\1</a>",
        escaped_text,
    )


def render_html_body(
    audience: str,
    child_first_name: str,
    highlights: list[str],
    schedule: list[str],
    clinical: list[str],
    media_lines: list[str],
    sender_name: str,
) -> str:
    """HTML body. Every interpolated value is escaped."""
    e = html.escape
    first = e(child_first_name)
    heading = {
        "clinician": f"A quick progress note on {first}:",
        "educator": f"A short update on {first} from home:",
        "family": f"Here's what's new with {first}:",
    }[audience]

    def section(title: str, items: list[str]) -> str:
        if not items:
            return ""
        lis = "".join(f"<li>{_inline_links(e(item))}</li>" for item in items)
        return (
            f"<h3 style=\"margin:16px 0 6px;font-size:15px;\">{e(title)}</h3>"
            f"<ul style=\"margin:0;padding-left:20px;\">{lis}</ul>"
        )

    parts = [
        "<p style=\"margin:0 0 4px;\">Hello,</p>",
        f"<p style=\"margin:8px 0;\">{heading}</p>",
        section("Highlights", highlights),
        section("Clinical notes", clinical if audience == "clinician" else []),
        section("Dates to know", schedule),
        section("Photos and videos", media_lines),
        f"<p style=\"margin:16px 0 0;\">- {e(sender_name or 'Family')}</p>",
    ]
    return (
        "<div style=\"font-family:Arial,Helvetica,sans-serif;font-size:14px;"
        "line-height:1.6;color:#1a1a1a;max-width:640px;\">"
        + "".join(parts)
        + "</div>"
    )


def media_bullet(media: dict, share_url: str | None) -> str:
    """One 'Photos and videos' bullet for a planned media item."""
    name = media["name"]
    if media["decision"] == "attach":
        return f"{name} (attached, {_fmt_size(media['size_bytes'])})"
    if share_url:
        return f"{name} (view online: {share_url})"
    return f"{name} (a private view link will be included)"


# --- Snapshot helpers -----------------------------------------------------------


def content_snapshot(
    subject: str,
    text_body: str,
    html_body: str,
    plan: list[dict],
    share_links: dict[int, str],
    template_key: str | None,
) -> str:
    """Freeze the exact sent content (immutable audit trail)."""
    return json.dumps(
        {
            "subject": subject,
            "text_body": text_body,
            "html_body": html_body,
            "attachments": [p for p in plan if p["decision"] == "attach"],
            "share_links": {str(k): v for k, v in share_links.items()},
            "template_key": template_key,
            "rendered_at": datetime.utcnow().isoformat() + "Z",
        },
        ensure_ascii=False,
    )


def recipient_snapshot(contact_id: int | None, display_name: str, address: str, roles: str) -> str:
    return json.dumps(
        {"contact_id": contact_id, "display_name": display_name, "address": address, "roles": roles},
        ensure_ascii=False,
    )
