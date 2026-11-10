# Suggested PR title

feat(email): Email Center (v6 Pass 5 local slice) + Bedrock draft assembler teaser

## What
- Safety core email_center.py: audience classes, disclosure policy + clinical scanner, PRIV-04 hard-block, 10 MiB MIME budget, attach-vs-link planner, HTML-escaped templates
- Admin-only routes /api/profiles/{id}/email: facts, recipients, drafts CRUD, EXACT preview, idempotent per-recipient send + outbox, outbound-only sent history, Bedrock ai-draft (flag-gated, never auto-sends)
- New tables: message_drafts, messages, message_events, outbox_jobs (additive)
- Frontend: EmailCenter composer (searchable multi-selects), reached from Gallery; honest console/logged vs ses/submitted statuses
- Tests: 17 adversarial gates (CONTACT-03, PRIV-04, mixed-audience, MAIL-01/02/03, auth/cross-profile, AI gates); full backend suite 126 passed
- Also merges docs/email-live-prod-notes (VERSION 0.7.0, README, deploy docs, backlog reconciliation)

## Not in this PR (remaining email taskings)
- 5.5 delivery-event ingestion (SNS endpoint + SES config set) + CloudWatch send-cap alarm
- Bedrock 5b full pass (provenance checks, cost caps)
- Owner live-send verification after deploy

## Verification
Backend 126 tests passing; frontend builds clean; live local demo: photo attaches / video becomes revocable share link / clinical leak rejected 422 / Bedrock draft from selected facts only.

## One-click PR URL (gh not installed locally)
https://github.com/vampireLibrarianMonk/life_planning/compare/master...feat/email-center-local?quick_pull=1
