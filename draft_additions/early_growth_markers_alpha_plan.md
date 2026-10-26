# Early Growth Markers — Alpha Integration Plan (companion to the corpus)

> Companion to `draft_additions/developmental_checkpoints_draft.md`. This is a
> **design / alpha-loop plan**, not code. It describes how we bring the
> multi-stage early-childhood growth markers into the app so a parent can
> **(1) configure** which stages are active per child and **(2) print** a clean,
> doctor-visit-friendly stage sheet — and the **iteration loop** to get there.
>
> Decisions below were shaped by a three-agent panel: an **app-competence**
> agent (grounded in the real models/routes/guards), a **mission-fit** judgment
> agent, and a **reviser** agent who reconciled the two.

---

## 1. Goal & alpha scope

**Mission framing (not scope creep):** the app already tracks ages 0–5 inside
the pillars (e.g. Spiritual 0–5, Financial birth–5, Education 3–6). Early Growth
Markers fill the pre-literate, pre-economy gap and act as the **0–5 on-ramp into
the lifelong pillars** — explicitly *formation, not a report card, not a medical
screen.*

**In scope for alpha**
- **Configure:** per child, activate/deactivate an age interval (2, 4, 6, 9, 12,
  18, 24, 36, 48, 60 mo); mark each item `not yet / emerging / practicing`;
  keep two free-text notes (one family-shared, one private).
- **Print:** a print-optimized stage sheet (one interval per sheet) suitable to
  take to a pediatrician visit.

**Out of scope for alpha** (future): scoring/analytics, reminders/age-based
auto-prompts, server-side PDF, cross-child comparison, a dedicated `Pillar` enum
value, importing graded school reports.

---

## 2. Data model mapping (ZERO schema change)

Store each marker as a **`PillarEntry`** row — no new table, no new enum value
(the app-competence agent flagged that a new `Pillar` enum value can't be added
cleanly: SQLite stores the enum as a `VARCHAR + CHECK` fixed at table-create, and
the boot migration (`ensure_columns`) only *adds columns* — it can't widen the
CHECK on the already-deployed DB. So we reuse an existing pillar + a category tag).

| Concept | PillarEntry field | Value |
|---|---|---|
| Home pillar | `pillar` | `education` (existing enum value) |
| Feature tag | `category` | `devcheck` (milestones) / `devcheck_private` (worries) |
| Is a framework goal | `is_milestone` | `1` |
| Item text | `title` | the observable item, e.g. "Waves bye-bye" |
| Age interval label | `age_band` | `"2mo"`, `"12mo"`, `"24mo"`, … |
| Sort key | `age_years` | integer **months** (2,4,6,9,12,18,24,36,48,60) |
| Domain | (encode in `content` prefix or a sub-group) | Social & Emotional, etc. |
| Mark | `status` | tri-state → 6-state mapping (below) |
| Notes | `content` / sub-entries | free text |

**Tri-state → `status` mapping** (status is a free `String(20)`, freely PATCHable):

| Sheet mark | `status` | Why |
|---|---|---|
| not yet | `not_started` | matches default for `is_milestone` rows |
| emerging | `in_progress` | "actively emerging" fits in_progress, not "introduced" |
| practicing | `complete` | consistently demonstrated |

`introduced`, `practicing`(status), `mastered` are **intentionally reserved/unused**
for these rows — documented so no one "fills them in" and breaks the tri-state UI.

**Interval ordering gotcha:** `age_band` is a string, so `"12mo"` sorts before
`"2mo"` lexically. The UI must **order by numeric `age_years`**, not `age_band`.

---

## 3. Privacy split (the one real design tension, resolved)

The milestones are celebratory and **family-readable**; a parent's *worries* are
not. Resolution — two categories, two routes, **both reusing existing guards**:

| Data | `category` | Served under | Who can read |
|---|---|---|---|
| Milestone items + "noticing & celebrating" note | `devcheck` | existing `/entries` (router `require_profile_access`) | admin + owning child + **family readonly** |
| "Questions & worries for the next check-up" | `devcheck_private` | a **new sub-route** gated `require_private_profile_access` | admin + owning child only (**readonly 403**) |

Writes everywhere stay `require_admin_or_child` (readonly blocked). This needs
**one extra handler** reusing an existing guard — no new guard, no schema change.
Normal education-pillar views and `/demo` must **filter out both** `devcheck`
categories (so they don't bleed into regular milestones; `/demo` is static and
excludes real data for free).

---

## 4. Configure UX (seed-on-demand)

- **Activate an interval** = create that interval's ~25 rows
  (`category=devcheck`, `age_band`, `is_milestone=1`, default `status=not_started`).
  Done via a small **server-side template route** that mirrors `seed_data.py`
  (the item template stays authoritative in Python, not hardcoded in the client).
  Must be **idempotent per interval** (re-activating doesn't double-insert).
- **"Active intervals"** = simply which intervals have rows (presence-of-rows;
  no config-flag table, no second source of truth).
- **Deactivate** = DELETE that interval's rows (cascade cleans sub-entries).
- **Mark an item** = PATCH `status` on the row (existing endpoint).
- Lives on the **Profile page** as its own "Early Growth Markers" section that
  queries `category=devcheck`; the normal education view excludes it.

---

## 5. Printable stage sheet (lowest-dependency)

- **Approach:** print-optimized HTML + `@media print` + `window.print()`.
  **No server-side PDF** (keeps `requirements.txt` / the Docker image lean — the
  app has no PDF capability today and we won't add one for alpha).
- **Layout:** one age interval per sheet — the pinned non-diagnostic banner at
  top, the 5 domains with their items, each item showing **empty labeled
  checkboxes** (not yet / emerging / practicing) so it's usable on paper, a
  child-name/date header, and the "what helps" tips.
- **Private worries are OMITTED from print** in alpha (they're parent-only; keep
  them on-screen, not on a sheet that may be handed around).
- A print-only CSS class hides app chrome (nav, buttons).
- Button lives on the Profile page's Early Growth Markers section.

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
1. **Backend seed/CRUD** — the templated seed route (`devcheck`) + the private
   worries sub-route (`devcheck_private`); category filtering in existing views;
   tests (incl. readonly 403 on the private route; family can read milestones).
2. **Configure UI** — Profile-page section: activate/deactivate an interval,
   mark items, the two notes. One interval wired end-to-end first (12mo pilot).
3. **Print sheet** — `@media print` stage sheet for one interval; verify on paper.
4. **Scale** — remaining intervals via the template; a11y + walkthrough pass.

**Review gate (runs every slice before sign-off):** reuse the agent panel —
app-competence (does it match real code?), mission-fit (does it stay formation,
not clinical?), reviser (apply fixes) — plus the existing automated gates
(pytest, pre-commit, Playwright a11y/walkthrough).

**Definition of done for alpha**
- Corpus labels/title/banner/field-split updated (DONE — see corpus doc).
- Idempotent seed + deactivate route; tri-state→status mapping wired.
- Milestones + "celebrating" note family-readable; "worries" on the private
  route (verified: readonly → 403, admin + owning child → 200).
- Normal education views **and** `/demo` filter out both `devcheck` categories.
- Print view with the pinned non-diagnostic banner; worries omitted from print.
- Frontend sorts intervals by numeric `age_years`.
- Net: **zero schema/enum/migration change**; exactly one added private
  sub-route reusing an existing guard; all changes additive.

---

## 7. Guardrails carried over (non-negotiable)

- **Non-diagnostic, non-scoring, no medical advice.** The pinned banner is
  on-screen *and* on the printed sheet — not fine print.
- **Formation voice**, not clinical: "not yet / emerging / practicing"; no
  "assessment / baseline / deficit / behind / needs practice."
- **Original content only** (no ASQ reproduction) — already review-passed.
- **Visibility:** family-readable milestones, parent-only worries, never on
  `/demo`.

---

## 8. Open questions / decisions for Patrick + Sara

1. **Domain encoding:** keep domain as a heading grouping in the UI only, or also
   persist it in `category` (e.g. `devcheck:social_emotional`) for filtering?
   (Recommend: persist a domain tag for clean grouping; still no schema change.)
2. **Who marks items** — parents only, or the child too (child role can write)?
   Affects whether the child sees an editable vs. read-only sheet.
3. **Print scope:** one interval per sheet (recommended) vs. an "all active
   intervals" booklet.
4. **Worries field on print:** omit for alpha (current plan) — confirm that's the
   behavior you want, or a separate parent-only print.
