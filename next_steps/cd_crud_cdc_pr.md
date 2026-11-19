# Child Development PR — title + description (pre-filled URL at the end)

## TITLE

feat(cd): 'doing' rename, legend, print filename, domain CRUD, CDC crosswalk + 30mo

## DESCRIPTION

# Child Development — terminology, legend, print output, full CRUD, CDC due diligence

Four owner-requested enhancements to the Child Development section, plus a
CDC due-diligence pass over the whole corpus.

## 1. Terminology: "practicing" → "doing"
Display-only rename of the tri-state mark (not yet / emerging / **doing**).
DB status values are unchanged (`not_started`/`in_progress`/`complete`), so
existing marks keep working with zero migration.

## 2. Legend (page + printed sheet)
A legend now explains each mark, on the age-group view and in the printed
sheet: **not yet** = not observed in this stage yet (every child moves at
their own pace) · **emerging** = attempted sometimes or with help (the skill
is forming) · **doing** = done reliably and independently. The
non-diagnostic banner stays pinned.

## 3. Print output: well-formed filename + full child name
- Printing now sets `document.title` to
  **`YYYYMMDD-HHMMSS-<age band>-<child full name>`** (dashes between values,
  e.g. `20261119-091242-12mo-Robert Flanigan`) — browsers use it as the
  default "Save as PDF" filename — and restores the previous title after.
- A **print-only header** on the sheet carries the child's **full name**, the
  age-group label, the print date, and the legend. Screen-only chrome
  (buttons, navigation) is hidden in print via CSS.

## 4. Full CRUD: categories AND line items
- **Domain (category) CRUD**: create, rename, and delete categories per age
  group — built-in and parent-created. Deletes clean up gallery links but
  NEVER the canonical media. Renames rewrite the category suffix on every row.
- **Custom domains render**: the age-group route previously dropped any
  category outside the five built-ins; it now renders parent-created domains
  (humanized labels) after the built-ins, and drops built-in keys that were
  renamed away or emptied.
- **Per-item edit-in-place** added (✎ → inline input → save), completing CRUD
  on every line item, existing or new.
- **Seed safety**: re-running the checklist sync on an active age group is an
  idempotent TOP-UP — it adds new corpus items and never touches parent marks
  or custom items. Renaming away a built-in domain is honored (with an honest
  note that a later sync re-adds built-in items under their original key).

## 5. CDC due diligence (corpus augmented)
The corpus was cross-checked against the CDC "Learn the Signs. Act Early."
checklists (2–60 months). Gaps filled in our own words, including the
owner-cited **24mo social-emotional item: "Notices when others are hurt or
upset — pauses or looks sad when someone is crying"** — plus 4mo chuckles,
6mo laughs + raspberries, 9mo crawling, 12mo open-cup drinking, 18mo copying
chores, 24mo 50-words + both-hands coordination + reaction-checking, 36mo
drop-off calming + stringing beads + dressing, 48mo pretend-identity +
pouring + unbuttoning, 60mo buttoning. The **missing 30-month age group was
added** (CDC publishes it; our corpus skipped it). Full crosswalk documented
in `draft_additions/cdc_milestones_crosswalk.md`.

## Compatibility (zero-touch)
Everything is additive and per-profile: Robert's existing marks keep working;
the new CDC items reach existing profiles through the idempotent seed top-up
(one click per active age group); custom domains/items are per-profile rows
the checklist sync never touches. Verified locally with temp profiles
(seed → customize → re-seed → no duplication or loss → rename/delete → print).

## Tests
9 new tests (DOM-01..05 domain CRUD incl. gallery-link cleanup + media
preservation, SEED-02/03 top-up idempotency, CAT-30, auth wiring). Full
backend suite: **148 passing**. Frontend builds clean; ruff clean.
