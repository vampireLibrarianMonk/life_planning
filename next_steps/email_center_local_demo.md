# Email Center — LOCAL demo (v6 Pass 5 slice + Bedrock 5b teaser)

Built 2026-11-10 on branch `feat/email-center-local`. **LOCAL ONLY — nothing
deployed.** Server: `http://localhost:8000` (dev DB `life_plan_dev.db`,
console email backend — no real email is ever sent).

## How to see it in the UI
1. Server already running (or restart:
   `cd app/backend && DATABASE_URL="sqlite:///life_plan_dev.db" BEDROCK_DRAFT_ENABLED=1 ../../.venv/bin/python -m uvicorn main:app --port 8000`)
2. Open http://localhost:8000 → log in `admin` / `changeme`
3. Profile **Robert Demo** → **Gallery** → **✉️ Email Center**
4. Pick recipients → highlights → media → Compose (or "✨ Draft with Bedrock")
   → Preview (exact final) → Confirm & Send

## What was demonstrated live (via the API)
- **Sample A — accomplishment + photo:** family recipient (Grandma), fact
  "Stacks three blocks [complete]", photo `block-tower-accomplishment.jpg`
  → preview shows the photo **attaches** (1 KB, within the 10 MiB encoded
  budget) → sent → status `console/logged` (honest: logged, not delivered).
- **Sample B — video:** same recipient, `first-steps-video.mp4` → preview
  shows the video **never attaches**; at send a real revocable share link was
  minted and embedded:
  `http://localhost:8000/share/Sv8AbforqPYmV92onbBXMsKCFEa99qf_celCUxM7sfE`
  (7-day expiry, token stored hashed only).
- **Bedrock AI draft (Pass 5b teaser):** live Converse call to
  `amazon.nova-lite-v1:0` produced a warm, fact-bound draft ("Robert's
  Milestone: Stacking Three Blocks") using ONLY the selected facts + note;
  status stayed `draft` (human approval required; never auto-sent).
- **Disclosure gate (live 422):** a family draft containing "speech therapy /
  diagnosis" was REJECTED with the honest message to split into a separate
  clinician draft. Private worries notes are structurally excluded from the
  composer AND any draft body containing them verbatim is rejected (PRIV-04).

## What shipped (code)
- Backend: `email_center.py` (policy/templates/MIME budget), `routes/email_center.py`
  (facts/recipients/drafts/preview/send/messages/ai-draft), models
  (`message_drafts`, `messages`, `message_events`, `outbox_jobs`), schemas.
- Frontend: `EmailCenter.jsx` (compose → exact preview → explicit send → sent
  history), Gallery "✉️ Email Center" entry, api.js client functions.
- Tests: `tests/test_email_center.py` — 17 tests covering CONTACT-03, PRIV-04,
  mixed-audience split, MAIL-01/02/03, auth + cross-profile gates, and the AI
  path (flag-gated, never auto-sent, policy-checked). **Full backend suite:
  126 passed.**
- Demo data: `seed_email_demo.py` (idempotent; profile id=2, photo id=1,
  video id=2, objective id=591, grandma method=2, doctor method=3).

## Not done yet (per the backlog plan)
- 5.5 delivery-event ingestion (SNS→endpoint), CloudWatch send-cap alarm.
- Real SES send path locally (console backend is the local default by design).
- SMS (Pass 6) — still blocked on A2P 10DLC registration (owner-gated).
