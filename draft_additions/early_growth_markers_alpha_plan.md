# Early Growth Markers — Alpha Integration Plan (companion to the corpus)

> **STATUS: BUILT & LIVE (2026-10-27).** This started as a design/alpha plan;
> the alpha (configure + objective CRUD + accomplishment photos + private
> worries note + print stage sheet) is now implemented as the **"Child
> Development"** dashboard section and deployed. Code:
> `app/backend/child_development.py`, `app/backend/routes/child_development.py`,
> `app/frontend/src/components/ChildDevelopment.jsx`; tests
> `app/backend/tests/test_child_development.py` + `app/frontend/tests/
> child_development.spec.js` (e2e verified green against the live deploy). The
> sections below are retained as the as-designed record.
>
> Companion to `draft_additions/developmental_checkpoints_draft.md`. Describes
> how the multi-stage early-childhood growth markers integrate so a parent can
> **(1) configure** which stages are active per child and **(2) print** a clean,
> doctor-visit-friendly stage sheet — and the **iteration loop** that built it.
>
> Decisions below were shaped by a three-agent panel: an **app-competence**
> agent (grounded in the real models/routes/guards), a **mission-fit** judgment
> agent, and a **reviser** agent who reconciled the two.

---

## 1. Goal & alpha scope

**Mission framing (not scope creep):** the app already tracks ages 0–5 inside
the pillars (e.g. Spiritual 0–5, Financial birth–5, Education 3–6). Child
Development fills the pre-literate, pre-economy gap and acts as the **0–5 on-ramp
into the lifelong pillars** — explicitly *formation, not a report card, not a
medical screen.* It lives as its **own dashboard section, directly below Life
Maps** (same level as Life Maps — a section, not a pillar).

**In scope for alpha**
- **Configure:** per child, activate/deactivate an **age group** (2, 4, 6, 9, 12,
  18, 24, 36, 48, 60 mo); under each group, break out **objectives** by domain;
  full **CRUD on each objective** (add/edit/mark/delete); mark each objective
  `not yet / emerging / practicing`; keep two free-text notes (one family-shared,
  one private).
- **Photos:** upload accomplishment photos/attachments on any objective.
- **Print:** a print-optimized stage sheet (one age group per sheet) suitable to
  take to a pediatrician visit.

**Out of scope for alpha** (future): scoring/analytics, reminders/age-based
auto-prompts, server-side PDF, cross-child comparison, turning `pillar` into a
first-class validated string, importing graded school reports.

---

## 2. Where it lives — a dashboard section, same level as Life Maps

**Child Development is its own top-level section on the Profile dashboard,
rendered immediately BELOW "Life Maps"** — NOT one of the 14 pillar cards and
NOT nested inside the `education` pillar.

This mirrors exactly how **Life Maps** already works: Life Maps is a
dashboard-level `<h2>` section (Profile.jsx ~line 476, commented "not pillars")
whose cards open dedicated views via sentinel keys
(`setActivePillar('__life_chart__')`, `'__belonging__'`). Child Development uses
the same convention with a new sentinel, e.g. `'__child_development__'`.

**Why this resolves the enum problem for free:** because it's a dashboard
section (like Life Maps), NOT a `Pillar` enum member, we do **not** add a new
`Pillar` value — so we avoid the SQLite `VARCHAR + CHECK` enum-migration wall
the app-competence agent flagged. Zero schema change stands.

**Hierarchy:** `Child Development → age group → domain → objective`.

```
Child Development            (dashboard section, just below Life Maps)
├── Age group: ~2 months     (a card)
│     ├── Social & Emotional (domain heading)
│     │     └── objective: "Begins to smile back"  [CRUD menu] [📷 photos]
│     ├── Communication & Language
│     ├── Thinking & Problem-Solving
│     ├── Gross Motor
│     └── Fine Motor
├── Age group: ~4 months     (a card)
│     └── …
└── … up to ~5 years
```

---

## 3. Data model mapping (ZERO schema change)

Store each **objective** as a **`PillarEntry`** row — no new table, no new
`Pillar` enum value (Child Development is a dashboard section, not a pillar).

| Concept | PillarEntry field | Value |
|---|---|---|
| Section marker | `category` | `child_development` (objectives) / `child_development_private` (worries) |
| Domain within an age group | `category` suffix | e.g. `child_development:social_emotional` (persist the domain for clean grouping) |
| Framework objective | `is_milestone` | `1` |
| Objective text | `title` | e.g. "Waves bye-bye" |
| Age group | `age_band` | `"2mo"`, `"12mo"`, `"24mo"`, … (`"5yr"` etc.) |
| Sort key | `age_years` | integer **months** (2,4,6,9,12,18,24,36,48,60) |
| Mark | `status` | tri-state → status mapping (below) |
| Parent note / detail | `content` | free text |
| Accomplishment photos | `EventAttachment` | attached to the objective's `PillarEntry` via the existing upload routes |

> `pillar` is set to a stable existing value (e.g. `education`) only to satisfy
> the non-null column; the UI never surfaces these under that pillar — they are
> addressed exclusively through the Child Development section + the
> `child_development*` category. (If we later decide `pillar` should become a
> plain validated string so Child Development can be a true first-class value,
> that's a separate, optional migration — not needed for alpha.)

**Tri-state → `status` mapping** (status is a free `String(20)`, PATCHable):

| Mark | `status` | Why |
|---|---|---|
| not yet | `not_started` | default for `is_milestone` rows |
| emerging | `in_progress` | active emergence |
| practicing | `complete` | consistently demonstrated |

`introduced`, `practicing`(status), `mastered` are **reserved/unused** here.

**Ordering gotcha:** `age_band` is a string (`"12mo"` sorts before `"2mo"`); the
UI must order age groups by numeric `age_years`.

---

## 4. Privacy split (resolved; unchanged by the restructure)

| Data | `category` | Served under | Who can read |
|---|---|---|---|
| Objectives + accomplishment photos + "noticing & celebrating" note | `child_development` | existing `/entries` router (`require_profile_access`) | admin + owning child + **family readonly** |
| "Questions & worries for the next check-up" | `child_development_private` | a **sub-route** gated `require_private_profile_access` | admin + owning child only (**readonly 403**) |

Writes stay `require_admin_or_child` (readonly blocked). Photos use the existing
`EventAttachment` upload/serve routes (already attach to a `PillarEntry`), so
accomplishment photos are **family-readable** like the objectives they hang on.
Regular pillar/education views and `/demo` must **exclude** both
`child_development*` categories.

---

## 5. Section UX — menu, CRUD, and photos

**Dashboard section (`## Child Development`, just below Life Maps):** a row of
**age-group cards** (2mo … 5yr). Only age groups the parent has activated show;
an "+ Add age group" affordance activates more.

**Age-group view** (opens on card click, like a Life Maps view):
- Objectives grouped under the **5 domain headings**.
- Each objective row has:
  - the **tri-state marker** (not yet / emerging / practicing),
  - a **CRUD menu** — edit title/detail, change mark, **delete**, and
    **"+ Add objective"** to create a custom one for this age group/domain,
  - a **📷 photos** control to **upload accomplishment photos/attachments**
    (reuses the existing attachment upload; thumbnails shown inline),
  - optional first-noticed date.
- The two notes: **"noticing & celebrating"** (family-shared) and
  **"questions & worries"** (parent-only, private route).
- A **"Print stage sheet"** button (see §6).

**Configure (seed-on-demand):** activating an age group creates that group's
objective rows from a server-side template (mirrors `seed_data.py`; idempotent,
no double-insert). "Active groups" = which groups have rows (presence-of-rows;
no config-flag table). Deactivate = DELETE that group's rows (cascade cleans
sub-entries + attachments).

**Marking / editing** = PATCH/POST/DELETE on the existing `/entries` endpoints.

---

## 6. Printable stage sheet (lowest-dependency)

- **Approach:** print-optimized HTML + `@media print` + `window.print()`.
  **No server-side PDF** (keeps `requirements.txt` / the image lean).
- **Layout:** one **age group** per sheet — pinned non-diagnostic banner at top,
  the 5 domains with their objectives, each objective showing **empty labeled
  checkboxes** (not yet / emerging / practicing) for paper use, a
  child-name/date header, and the "what helps" tips.
- **Private worries are OMITTED from print** in alpha.
- A print-only CSS class hides app chrome. Button lives in the age-group view.

---

## 6. The alpha loop (iteration cycle)

```
  (0) corpus approved by Patrick + Sara   ← we are here
       │
  (1) SPEC one slice ──► (2) BUILD it ──► (3) 4-GATE REVIEW ──► (4) PARENT SIGN-OFF ──► next slice
       ▲                                        │
       └──────────────── refine ◄───────────────┘
```

**Slices, in order (each a loop iteration):**
1. **Backend seed/CRUD** — the templated seed route (`child_development`) + the
   private worries sub-route (`child_development_private`); category filtering in
   existing views; reuse the existing `EventAttachment` upload for objective
   photos; tests (incl. readonly 403 on the private route; family can read
   objectives + photos).
2. **Dashboard section + age-group view** — add the `## Child Development`
   section directly below Life Maps with age-group cards; the age-group view with
   objectives grouped by domain, the per-objective CRUD menu, the tri-state
   marker, photo upload, and the two notes. Wire **one age group end-to-end
   first (12mo pilot)**.
3. **Print sheet** — `@media print` stage sheet for one age group; verify on paper.
4. **Scale** — remaining age groups via the template; a11y + walkthrough pass.

**Review gate (runs every slice before sign-off):** reuse the agent panel —
app-competence (does it match real code?), mission-fit (does it stay formation,
not clinical?), reviser (apply fixes) — plus the existing automated gates
(pytest, pre-commit, Playwright a11y/walkthrough).

**Definition of done for alpha**
- Corpus labels/title/banner/field-split updated (DONE — see corpus doc).
- Child Development renders as its own dashboard section **directly below Life
  Maps** (age-group cards → age-group view).
- Idempotent seed + deactivate per age group; tri-state→status mapping wired;
  full objective CRUD; accomplishment photo upload working.
- Objectives + photos + "celebrating" note family-readable; "worries" on the
  private route (verified: readonly → 403, admin + owning child → 200).
- Normal pillar/education views **and** `/demo` exclude both
  `child_development*` categories.
- Print view with the pinned non-diagnostic banner; worries omitted from print.
- Frontend sorts age groups by numeric `age_years`.
- Net: **zero schema/enum/migration change**; one added private sub-route
  reusing an existing guard; all changes additive.

---

## 7. Guardrails carried over (non-negotiable)

- **Non-diagnostic, non-scoring, no medical advice.** The pinned banner is
  on-screen *and* on the printed sheet — not fine print.
- **Formation voice**, not clinical: "not yet / emerging / practicing"; no
  "assessment / baseline / deficit / behind / needs practice."
- **Original content only** (no ASQ reproduction) — already review-passed.
- **Visibility:** family-readable objectives + photos, parent-only worries,
  never on `/demo`.

---

## 8. Decisions (confirmed by Patrick + Sara, 2026-10-27)

1. **Placement:** ✅ Child Development is its own dashboard section at the **same
   level as Life Maps, placed directly below it** (not a pillar, not inside
   education).
2. **Top-level cards = age groups;** drilling in shows domains → objectives.
3. **Visibility:** ✅ keep the split — objectives + accomplishment photos are
   **family-readable** (grandparents can see); the "questions & worries" note is
   **parent/child-only** (private route).

### Still open (nice-to-finalize before/with slice 2, not blocking slice 1)
- **Who marks/edits objectives:** parents only, or the child too? (Child role
  *can* write today; decide whether the child's view is editable or read-only.)
- **Print scope:** one age group per sheet (planned) vs. an "all active groups"
  booklet.
- **Worries on print:** omitted in alpha (planned) vs. a separate parent-only
  print.
