# How to Integrate New Capabilities

This document tells an LLM (or developer) how the Life Plan Tracker application is structured, where new ideas belong, and how to integrate them without breaking existing functionality.

---

## Application Architecture

```
life_plan/
├── app/backend/
│   ├── main.py              → FastAPI entry point, router mounting
│   ├── models.py            → SQLAlchemy ORM models (12 tables)
│   ├── schemas.py           → Pydantic request/response schemas
│   ├── auth.py              → JWT + role-based access (admin/child/readonly)
│   ├── database.py          → SQLite connection
│   ├── seed_data.py         → BOUNTIES list + MILESTONES dict (seeded on profile creation)
│   ├── programs.py          → PROGRAMS list (program card definitions)
│   ├── program_phases.py    → PROGRAM_PHASES dict (tier → phase label per program)
│   ├── research_topics.py   → Topic banks for research-style bounties
│   └── routes/
│       ├── profiles.py      → Profile CRUD + reseed logic
│       ├── pillars.py       → Pillar entry CRUD (milestones, notes, events)
│       ├── economy.py       → Bounties, behavior incidents, wishlist, earnings
│       ├── discernment.py   → 10-category journal CRUD
│       ├── discernments.py  → Life-path discernments (career, vocation)
│       ├── events.py        → File attachments
│       ├── docs.py          → Serve filtered planning docs (admin)
│       └── users.py         → Auth endpoints
├── app/frontend/src/pages/
│   ├── Profile.jsx          → Main profile view (pillars, programs, discernment)
│   ├── Economy.jsx          → Bounty board (embedded in Profile)
│   ├── Dashboard.jsx        → Profile list
│   └── Login.jsx            → Auth
├── docs/                    → 22 planning documents (conceptual framework)
├── diagrams/                → PlantUML source + rendered PNGs
└── new_capability/          → Incoming ideas awaiting integration
```

---

## Core Concepts

### Pillars (14)
Development domains tracked with age-banded milestones. Each milestone has a 6-state status progression: not_started → introduced → in_progress → practicing → complete → mastered.

**Pillar keys:** spiritual, financial, education, character, life_skills, heritage, economy, resilience, dimensional_navigation, civic, scientific_reality_testing, inheritance_burden_stewardship, catholic_formation, secular_sacred_formation

### Programs (10)
Structured bounty tracks that group bounties by category. A program card appears in the UI showing all bounties within its categories.

### Bounties
Tasks with rewards (in cents). Can be one-time or repeatable (with decay). Organized by category → program.

### Milestones
Age-banded developmental goals within a pillar. Seeded from `seed_data.py`.

### Discernment Journal (10 categories)
Reflective entries on fundamental domains (health, math, science, civics, relationships, faith, tradition, law, network, calling).

---

## Age Bands

| Band | Phase | Typical Development |
|------|-------|-------------------|
| 0-2 | Foundation | Infancy — receives, observes |
| 2-3 | Foundation | Toddler — emerging skills |
| 3-5 | Foundation | Preschool — readiness |
| 6-12 | Exploration | Ask, test, discover |
| 13-18 | Formation | Build conviction, test models |
| 18-25 | Launch | Independent application |
| 25-35 | Stewardship | Transmit, protect, build |

---

## Bounty Tiers (10)

bronze, silver, gold, platinum, diamond, obsidian, legendary, covenant, ooh_shiny, ironforged

---

## Integration Decision Tree

When integrating a new capability, determine:

### 1. Does it add bounties, milestones, or both?

- **Bounties only** → Add to `seed_data.py` BOUNTIES list
- **Milestones only** → Add to appropriate `MILESTONES[pillar_key]` list
- **Both** → Add both

### 2. Does it belong to an existing program or need a new one?

- **Existing program** → Use that program's category (e.g., `formation_study`, `civic_chain_of_command`)
- **New program** → Add to `programs.py`, add phases to `program_phases.py`, create a new category

### 3. Does it need a new pillar?

Almost never. The 14 pillars cover the full developmental landscape. New content almost always fits into an existing pillar. If it genuinely doesn't fit anywhere, that's a major architectural decision.

### 4. Does it require schema changes?

- **No schema changes** (most common) → Bounties and milestones use existing tables. Just add seed data.
- **New record type** → Requires new model in `models.py`, new schema in `schemas.py`, new route file, new frontend display. This is a significant effort.
- **New fields on existing tables** → Requires migration consideration (SQLite doesn't support easy ALTER for constraints).

### 5. Does it require new dependencies?

Flag any new Python or JavaScript packages. Use pinned versions. Verify licensing.

---

## How to Add a Bounty

Add a dict to the `BOUNTIES` list in `app/backend/seed_data.py`:

```python
{
    "tier": "silver",                    # bronze/silver/gold/platinum/diamond/obsidian/legendary/covenant/ooh_shiny/ironforged
    "title": "Short descriptive title",
    "description": "One sentence explaining what the child does.",
    "requirements": "Detailed list of what must be completed.",
    "criteria": "How the parent judges completion. What to reject.",
    "reference": "docs/XX_relevant_doc.md#section",
    "reward_amount": 1500,              # cents ($15.00)
    "pillar": "civic",                  # one of the 14 pillar keys
    "age_band": "13-18",               # 0-2, 2-3, 3-5, 6-12, 13-18, 18-25, 25-35
    "category": "program_category",     # groups bounties into programs
    "repeatable": 1,                    # 0=one-time, 1=repeatable
    "decay_divisor": 2,                 # divide reward by this each completion (None for no decay)
    "reset_days": 30,                   # days before decay resets to full value (None=never)
}
```

---

## How to Add Milestones

Add dicts to the appropriate `MILESTONES[pillar_key]` list:

```python
{"age_band": "13-18", "title": "Description of the milestone", "category": "Formation"},
```

Category must match the phase: Foundation (0-2/2-3/3-5), Exploration (6-12), Formation (13-18), Launch (18-25), Stewardship/Consolidation (25-35).

---

## How to Add a Program

1. Add to `app/backend/programs.py`:
```python
{
    "key": "program_key",
    "title": "Display Title",
    "icon": "🎯",
    "description": "Short description.",
    "categories": ["bounty_category_1", "bounty_category_2"],
},
```

2. Add phases to `app/backend/program_phases.py`:
```python
"program_key": {
    "bronze": "Phase 1: Name",
    "silver": "Phase 2: Name",
    "gold": "Phase 3: Name",
    ...
},
```

3. Add bounties with matching category to `seed_data.py`.

---

## How to Reseed Existing Profiles

After adding seed data, existing profiles need reseeding:
- UI: Click "🔄 Sync Milestones & Bounties" on the profile dashboard
- API: `POST /api/profiles/{id}/reseed`
- Reseed adds new bounties/milestones, corrects age_bands, refreshes bounty metadata — never deletes or resets progress.

---

## Guardrails

- **Never delete existing milestones or bounties from seed_data** — they may already exist in user databases. Mark as deprecated if needed.
- **Never change a bounty's (category, title) tuple** — that's the unique key for reseed matching.
- **Test with** `python -c "import seed_data; print(len(seed_data.BOUNTIES))"` after changes.
- **Build frontend** with `cd app/frontend && npm run build` to verify no JSX errors.
- **Verify app loads** with `python -c "from main import app; print('OK')"`.
- **Update README, SBOM, VERSION** when adding significant content.

---

## Files to Touch (Typical Integration)

| What you're adding | Files to modify |
|-------------------|----------------|
| Bounties for existing program | `seed_data.py` |
| Bounties for new program | `seed_data.py`, `programs.py`, `program_phases.py` |
| Milestones | `seed_data.py` |
| New planning document | `docs/XX_name.md`, README project structure |
| New route/model | `models.py`, `schemas.py`, `routes/new.py`, `main.py` |
| Frontend changes | `app/frontend/src/pages/Profile.jsx` or `Economy.jsx` |

---

## Current Counts (as of integration)

| Metric | Value |
|--------|-------|
| Milestones | 540 |
| Bounties | 118 |
| Programs | 10 |
| Pillars | 14 |
| Discernment categories | 10 |
| Planning documents | 23 |
