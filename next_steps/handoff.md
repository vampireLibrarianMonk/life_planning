# Handoff — current state (refreshed 2026-10-27)

Concise current-state snapshot (replaces the earlier Child-Development planning
note, which is now shipped). Authoritative details live in the linked docs.

## Live system
- **Life Plan Tracker** — FastAPI + React SPA, SQLite (Litestream→S3), on AWS
  App Runner, dual-region (us-east-1 primary / us-west-2 warm standby), Route 53
  failover, WAF, custom domain + managed TLS. Live at
  https://life-planning.my-deployment.com.
- **Roles:** admin (parents), child (own profile only), readonly (extended
  family, view-only). ~7 accounts incl. robflan (child), 3 grandparents.
- **Email:** SES, DKIM-aligned domain sender
  `no-reply@life-planning.my-deployment.com`, production access both regions.

## Shipped features (built + deployed + tested)
- Pillars, family economy/bounties, discernment journals, Life Maps.
- **Readonly hardening**, **child self-write lockdown**, **cross-child isolation**,
  **private-by-design** data (behavior log / journals / financial totals).
- **Public `/demo`** (static fake data, no DB).
- **Archive / restore / full-clean delete** with a signed backup-first handshake.
- **Child Development** section (early-growth markers, ages ~2mo–5yr): age-group
  cards → objective CRUD + accomplishment photos + private worries note + print
  stage sheet. Family-readable objectives, parent/child-only worries.
- **Security remediation** (3-agent review): authorized blob serving (`?token=`),
  hardened `/restore`, trimmed `/api/health`. See `deploy/SECURITY_REVIEW.md`.

## Key docs
- `deploy/SECURITY_REVIEW.md` — full security posture + §10 re-review results,
  deferred items, and the owner-only infra checklist.
- `deploy/DEPLOYMENT_STEPS.md` — as-built runbook (incl. SES/DKIM).
- `next_steps/02_backlog.md` — Manager's Dashboard (#1, specced), Child
  Development (#2, built), lineage (#3, reframed as a small Heritage enrichment).
- `next_steps/01_user_provisioning.md` — provisioning + role model.

## Test/deploy gates
- Backend: `.venv-test/bin/python -m pytest` (38 tests). Frontend: `npm run build`
  + Playwright (a11y + walkthrough + child_development). Pre-commit must be green.
- Deploy: `./deploy/build_push.sh` → both regions; verify `./deploy/monitor.sh`.
- Two venvs, both Python 3.12: `.venv` (runtime, mirrors Docker) / `.venv-test`.

## Open (owner)
- Deferred security items + infra checklist in `SECURITY_REVIEW.md` §10.
- Backlog #1 (Manager's Dashboard) ready to start; #3 (lineage) pending a
  "worth it?" decision.
