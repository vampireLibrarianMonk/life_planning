Three-agent panel (as you specified):
1. App-competence agent (grounded in real code) — found the feature fits with zero schema change: store markers as PillarEntry rows under the existing education pillar + a category=devcheck tag. It caught a
genuine gotcha — a new Pillar enum value can't be added cleanly because SQLite stores the enum as a VARCHAR+CHECK the boot migration can't widen — so reuse avoids a painful migration.
2. Mission-fit judgment agent — verdict "FIT WITH GUARDRAILS": ages 0–5 tracking is already native to the app (not scope creep), tone matches the "formation not scoring" ethos, but recommended reframing
away from clinical vocabulary and splitting sensitive notes to parent-only.
3. Reviser agent — reconciled the one real tension (family-readable milestones vs. parent-only worries) with a two-category / two-route split that reuses existing guards, no schema change.

Corpus revisions applied to developmental_checkpoints_draft.md:
- Retitled to "Early Growth Markers"; non-diagnostic line promoted to a pinned banner.
- Tri-state renamed not yet / emerging / practicing (sheds clinical tone; status mapping unchanged).
- Added domain→pillar bridges; split free-text into a family-shared "noticing & celebrating" note and a private "questions & worries" note (removed the stale "visible to family" line).

New companion doc early_growth_markers_alpha_plan.md:
- Data-model mapping (zero schema change), tri-state→status mapping, interval encoding + the age_years sort gotcha, the privacy split, seed-on-demand configure UX, the print-via-@media print stage sheet (no
new deps), the alpha iteration loop with the review gate, a definition of done, guardrails, and open questions for you + Sara.

Both docs are tracked in draft_additions/; source PDFs stay git-ignored in reference/. Docs only — nothing deployed.

The 4 open questions at the end of the plan are the decisions I need from you and Sara before building (domain encoding, who can mark items, print scope, and whether worries ever print). When you've
decided, slice 1 is the backend seed/CRUD + the private worries route with tests.
