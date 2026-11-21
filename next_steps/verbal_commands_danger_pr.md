## TITLE

feat(cd): verbal-command + danger-awareness milestones (7 additions, owner-approved) + walkthrough capture

## DESCRIPTION

# Verbal commands + sense of danger — 7 research-backed milestones (owner-approved)

Applies the research-backed additions from
`draft_additions/verbal_commands_danger_research.md` (APPROVED by the owner)
to the Early Growth Markers corpus, and extends the Playwright
screen-capture walkthrough to cover them.

## Verbal commands (communication domain) — extends the existing progression

Driven by working-memory growth: each step up roughly doubles the memory
load. A child who "doesn't listen" at 3 often cannot yet HOLD a 3-step
chain.

- **36mo**: "Follows instructions with two or three steps in a row (take off
  your shoes and put them in the closet)."
- **48mo**: "Carries out a multi-step instruction after a delay (when we get
  home, hang up your coat)."
- **60mo**: "Follows complex multi-step instructions with conditionals (after
  you hang your coat, wash your hands, then come to the table)."

Extends the existing 12mo (gesture-paired) → 18mo (1-step) → 24mo (2-step)
progression.

## Sense of danger (thinking domain — anticipating consequences)

A NEW physical-danger progression pairing with the existing body-safety and
unsafe-secrets items. Research: "sense of danger" is BUILT, not innate —
concrete rules + supervised practice + why-explanations; the real daily-risk
ranking for young children is traffic and water, not strangers.

- **24mo**: "Stops at the curb when told (holds an adult's hand near the
  street)."
- **36mo**: "Names the family danger rules when asked: hot things, sharp
  things, the street, water, and going with unknown adults."
- **48mo**: "Explains why each family danger rule exists (what could happen
  if it is broken)."
- **60mo**: "Applies the family danger rules without reminders in familiar
  places (kitchen, street curb, pool)."

## Playwright walkthrough extended

`cd_walkthrough.spec.js` now seeds the 36/48/60mo age groups via the API
(idempotent) and captures each view, asserting the new instruction-following
and danger-awareness items plus the alternating-legs stairs item from the
previous PR. Screenshots land in test-results/cd-walkthrough/.

## Verification

- All 7 additions asserted in the corpus; 15 CD tests passing; full backend
  suite green; ruff clean; frontend builds clean.
- Research doc marked APPROVED/APPLIED per the owner's sign-off.

## After merge

Deploy (build_push.sh), then "⟳ Sync new checklist items" on the 36/48/60mo
age groups (idempotent top-up; existing marks untouched).
