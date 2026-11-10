# Email Center PR — title + description (copy into the GitHub PR form)

**One-click URL (pre-fills title + body):** see `PR_URL` below / the link printed
at the end of this file. Or open
https://github.com/vampireLibrarianMonk/life_planning/compare/master...feat/email-center-local?quick_pull=1
and paste this description.

---

## TITLE

feat(email): Email Center (v6 Pass 5 complete) + Bedrock draft assembler + SES event pipeline

---

## DESCRIPTION

# Email Center — v6 Pass 5 (complete) + Bedrock 5b + SES event pipeline

Closes out the Email Center build plan in `next_steps/02_backlog.md` (§5):
a child-scoped Email Center where a parent composes an update from
**explicitly selected facts + media**, previews the **exact final email**,
and sends via SES with per-recipient disclosure policy, honest delivery
status, and a durable audit trail — plus the full SES delivery-event
pipeline and the Bedrock AI draft assembler with provenance + cost gates.

## What ships

### 1. Safety core (`email_center.py`) — the privacy rules live in ONE place
- **Audience classes**: every contact role maps to family / clinician /
  educator. A draft serves ONE audience; mixed audiences are rejected and
  must be split (never blended).
- **Disclosure policy**: clinical content requires a clinician audience AND
  an explicit `include_clinical` opt-in; a conservative clinical-term
  scanner adds defense in depth behind the flag (CONTACT-03).
- **PRIV-04**: `child_development_private` worries notes are structurally
  excluded from the composer's fact sheet AND any draft body containing
  them verbatim is rejected — not includable in this MVP, even to
  clinicians.
- **MIME budget (MAIL-02)**: 10 MiB encoded cap (SES limit 40 MB). Photos
  attach only within the recomputed running total; videos, documents, and
  over-cap images ALWAYS become revocable app share links — never silently
  dropped.
- Deterministic, HTML-escaped templates per audience; subjects omit
  clinical/child-identifying detail beyond the first name.

### 2. Backend (`routes/email_center.py`, admin-only)
- `GET /facts` — composer fact sheet (child-development objectives +
  recent events + gallery media); private worries structurally excluded.
- `GET /recipients` — linked contacts' verified email methods with the
  audience class the policy will assign.
- Drafts CRUD with disclosure validation at compose AND edit time; media
  ids validated cross-profile at compose time.
- `POST /drafts/{id}/preview` — the EXACT final: recipients expanded with
  verification shown, attach-vs-link plan with encoded sizes vs the cap,
  rendered text + HTML (share-token values exist only at send).
- `POST /drafts/{id}/send` — requires explicit `confirm: true` (MAIL-01);
  re-resolves + re-verifies recipients; one `Message` row PER RECIPIENT
  (no blended To/Cc); idempotency key `email:d{draft}:m{method}` makes
  retries non-duplicating (MAIL-03); share grants minted for link-decision
  media; statuses are honest (`console/logged` vs `ses/submitted`).
- `GET /messages` — outbound-only sent history with immutable snapshots
  (no inbox, EMAIL-04).
- Suppression: recipients suppressed after a bounce/complaint/opt-out are
  refused with an honest 422 (preview + send).
- `EMAIL_DAILY_SEND_CAP` (default 200/day, 0=off) — account-wide daily
  send cap, 429 beyond it.

### 3. SES delivery-event pipeline (Pass 5.5)
- `sns_verify.py`: real SNS SignatureVersion-1 verification (SHA1withRSA
  over the type-specific string-to-sign) with a strict signing-cert host
  allowlist (sns.amazonaws.com + regional); SubscribeURL confirmation
  restricted to the same allowlist. Stdlib urllib only — no new runtime
  HTTP dependency.
- `POST /api/email/events` (public): the SNS signature IS the
  authentication. SubscriptionConfirmation auto-confirms by visiting the
  SubscribeURL; Notifications are matched by SES MessageId →
  `message_events` row + truthful status: delivery → `delivered`;
  Permanent bounce → `failed` + suppress; complaint → `complained` +
  suppress; Temporary bounce stays submitted. Unknown provider ids are
  ignored (no oracle).
- `notify.SesSender` tags every send with `ConfigurationSetName` from
  `SES_CONFIG_SET` so events actually flow.

### 4. Bedrock draft assembler (Pass 5b, feature-flagged)
- `POST /drafts/ai-draft` gated by `BEDROCK_DRAFT_ENABLED=1`.
- The model receives ONLY parent-selected, policy-allowed facts + the
  parent's note; output is a DRAFT for human approval — never auto-sent.
- **Provenance gate**: rejects output containing a NUMBER absent from the
  selected facts/note (invented quantities/dates), the child's last name
  (only the first name is ever provided), or any contact display name
  (hallucinated people).
- **Cost caps**: `BEDROCK_MAX_TOKENS` (inference) and
  `BEDROCK_DAILY_AI_CAP` (default 25 drafts/day, 429 beyond).
- Output is re-validated by the same disclosure policy as hand-written
  drafts.

### 5. Data model (additive; prod-safe)
`message_drafts` (mutable working copy), `messages` (immutable
per-recipient snapshots), `message_events`, `outbox_jobs` — created via
`create_all`; no destructive migration.

### 6. Frontend
- `EmailCenter.jsx`: four-step composer (recipients → highlights → media →
  note) with **searchable multi-select comboboxes** (type-to-filter,
  removable chips, Enter/Escape keys), audience-colored recipient chips,
  mixed-audience warning, "✨ Draft with Bedrock" when enabled, EXACT
  preview panel (recipients, attachment plan, encoded MiB vs cap, full
  text body) behind an explicit Confirm & Send, and outbound-only sent
  history with transport/status honesty.
- Reached from **Gallery → ✉️ Email Center** (per the plan: not a 5th
  top-level peer). Readonly/child see a parent-only notice (backend is
  admin-only too).

### 7. AWS pipeline provisioned (via CLI, verified)
- SNS topic `life-planning-email-events` with an SES-publish policy scoped
  to the configuration set.
- HTTPS subscription to `https://life-planning.my-deployment.com/api/email/events`
  (pending — auto-confirms on first deploy of this branch).
- SES configuration-set event destination `sns-email-events`
  (SEND/BOUNCE/COMPLAINT/DELIVERY).
- `SES_CONFIG_SET=life-planning` set on BOTH App Runner regions.
- CloudWatch alarm `life-planning-ses-daily-sends` on the SES Send metric
  (threshold 200/day, matching the in-app cap).

### 8. Also includes
Merge of `docs/email-live-prod-notes` (VERSION 0.7.0 ledger, README,
deployment docs) so the branch merges cleanly to master; demo seed
(`seed_email_demo.py`) + local demo notes.

## Test ledger
- `tests/test_email_center.py` (17): CONTACT-03 clinical-leak rejection
  (scanner + flag rules), PRIV-04 (body + structural), mixed-audience
  split, unverified blocks preview/send, MAIL-01/02/03, sent-history
  immutability, admin-only wiring, cross-profile media/recipient denial,
  AI flag-gate / never-auto-sends / clinical-leak rejection.
- `tests/test_email_events.py` (12): SNS signature accept/tamper/
  allowlist, subscription confirmation, permanent-bounce → failed +
  suppress, delivery → delivered, complaint → complained + suppress,
  unknown-id no-oracle, suppression blocks send, daily send cap, AI
  provenance (invented number, last-name leak, clean accept), daily AI cap.
- `tests/test_readonly_enforcement.py`: `/api/email/events` exempted from
  the role-guard enumeration WITH justification (machine endpoint;
  signature-authenticated; tamper → 403 proven).
- **Full backend suite: 139 passing.** Frontend builds clean. ruff check +
  ruff-format clean (pre-commit hooks satisfied).

## CI fix included
`cryptography==50.0.2` added to `requirements.txt` — it is now a RUNTIME
dependency (sns_verify is imported at startup); CI's fresh env previously
had none, erroring 315 tests with ModuleNotFoundError.

## Deployment / live-verification plan (after merge)
1. `./deploy/build_push.sh` (promotes by digest to BOTH regions; env is
   preserved — `SES_CONFIG_SET` already set).
2. Confirm the SNS subscription activates (the deployed endpoint
   auto-confirms): `aws sns list-subscriptions-by-topic --topic-arn ...`.
3. Owner live test: compose → preview → send to `pmflani@gmail.com`;
   watch the Sent history progress `submitted → delivered` (delivery event
   round-trips through SNS → /api/email/events).

## Deliberately NOT in this PR
- SMS (Pass 6) — blocked on A2P 10DLC registration (owner-gated: EIN/
  sole-prop details, cost sign-off, consent records).
- Inbound email/SMS webhooks (Pass 7, optional).
- Bedrock invocation logging (stays OFF by default per the plan).

## Risk notes
- New public endpoint `/api/email/events` is signature-authenticated
  (verified before anything is trusted; tampered → 403; exempted from the
  role-guard meta-test with justification).
- All new tables are additive; prod (Robert) DB upgrades safely on boot.
- No real sends in automated tests (console backend / mocks); the single
  real send is the owner's manual live check.
