## TITLE

feat(cd): alternating-legs motor milestones (48mo + 60mo) with research doc + CD screen-capture walkthrough

## DESCRIPTION

# Alternating-legs motor milestones + CD screen-capture walkthrough

Adds the owner-approved alternating-legs gross-motor milestones to the Early
Growth Markers corpus, backed by a research document, plus a Playwright
screen-capture walkthrough of the Child Development section.

## Research base (draft_additions/alternating_legs_motor_research.md)

Evidence-based age windows, summarized from public-domain sources (CDC
movement milestones; Bayley-4 / PDMS-2 norm summaries; AAHPERD / PE Central
benchmarks):

- Stairs UP alternating feet: ~36-42mo (already covered at 36mo in our corpus)
- Stairs DOWN alternating feet: ~42-48mo (descending is harder: balance +
  depth perception)
- Playground ladder / rung climbing (alternating feet and hands): ~4-5yr
- Alternating legs WHILE jumping (jumping jacks / scissor jumps): ~5-6yr —
  a bilateral-coordination milestone; later than stairs because the child
  generates the alternation in the air without external step cues

## Corpus additions (owner-approved)

- **48mo gross motor**: "Walks down stairs alternating feet, holding the rail
  at first."
- **48mo gross motor**: "Climbs a playground ladder or climbing wall,
  alternating feet and hands."
- **60mo gross motor**: "Does jumping jacks or scissor jumps: jumps while
  alternating legs (and arms) in rhythm."

Each extends an existing progression (stairs, climbing, jumping) rather than
starting a new one. Reaches existing profiles via the idempotent checklist
sync button.

## Playwright screen-capture walkthrough (cd_walkthrough.spec.js)

Walks the Child Development section end-to-end and captures a full-page
screenshot at every step into test-results/cd-walkthrough/: dashboard,
age-group cards (incl. the 30mo group), and the 24mo detail view with the
bulleted legend, tri-state marks, domains, and the CDC 24mo item. Read-only.

## Also includes

- Legend `<ul>` gets the `cd-legend-list` class (test targeting).
- Backlog section 7: research record + pending-approval trail.
- Research doc marked APPROVED/APPLIED per the owner's 2026-11-21 sign-off.

## Verification

- seed_data + child_development import cleanly; new items asserted
- 15 CD tests passing; full backend suite green; ruff clean; frontend builds
