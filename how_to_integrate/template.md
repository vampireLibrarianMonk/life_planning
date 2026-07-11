# New Capability Template

Use this template when writing a new capability document for the Life Plan Tracker. Following this structure ensures the LLM can reference `how_to_integrate/main.md` and this document to produce a clean integration without ambiguity.

---

## Header

```markdown
# [Capability Name]
## [Subtitle — one line describing what this adds]
```

---

## Section 1: Placement

State clearly where this belongs in the application:

```markdown
## Placement

**Program:** [Existing program name OR "New program: Name"]
**Category:** [bounty category key, e.g., "formation_study", "civic_chain_of_command"]
**Pillar(s):** [Primary pillar + cross-linked pillars]
**Age bands:** [Which age bands this covers]
```

If creating a new program, also provide:
- Program key (snake_case)
- Program icon (emoji)
- Program description (one sentence)
- Phase labels (tier → phase name)

---

## Section 2: What It Adds

State explicitly what seed data this produces:

```markdown
## What This Adds

- [ ] Bounties: [count] ([list categories])
- [ ] Milestones: [count] ([which pillars/age bands])
- [ ] New program: [yes/no]
- [ ] Schema changes: [yes/no — if yes, describe]
- [ ] New dependencies: [yes/no — if yes, list with versions]
- [ ] New routes: [yes/no — if yes, describe]
```

---

## Section 3: Bounty Definitions

For each bounty, provide the complete dict (ready to paste into `seed_data.py`):

```python
{
    "tier": "",
    "title": "",
    "description": "",
    "requirements": "",
    "criteria": "",
    "reference": "",
    "reward_amount": 0,       # cents
    "pillar": "",
    "age_band": "",
    "category": "",
    "repeatable": 0,          # 0 or 1
    "decay_divisor": None,    # number or None
    "reset_days": None,       # number or None
},
```

---

## Section 4: Milestone Definitions

For each milestone, provide the dict (ready to paste into `seed_data.py` under the appropriate `MILESTONES[pillar_key]` list):

```python
{"age_band": "", "title": "", "category": ""},
```

Category must match phase:
- `0-2`, `2-3`, `3-5` → "Foundation"
- `6-12` → "Exploration"
- `13-18` → "Formation"
- `18-25` → "Launch"
- `25-35` → "Stewardship" or "Consolidation"

---

## Section 5: Guardrails

State what this capability must NOT do:

```markdown
## Guardrails

- Do not [specific anti-pattern]
- Do not [specific anti-pattern]
- Reject completions that [specific gaming vector]
```

---

## Section 6: Reward Budget

If this is a program or track with a target total:

```markdown
## Reward Budget

**Target total (completable by age X):** $[amount]
**Repeatable lifetime value:** $[amount] per cycle

| Tier | Bounties | Subtotal |
|------|----------|----------|
| Bronze | X | $Y |
| Silver | X | $Y |
| ...  | ... | ... |
```

---

## Section 7: Cross-References

```markdown
## Cross-References

- Document [XX]: [how it connects]
- Pillar [name]: [what milestone or concept links]
- Program [name]: [if bounties overlap or prerequisite]
```

---

## Section 8: Schema Changes (if any)

If the capability requires new database tables or fields:

```markdown
## Schema Changes

### New Table: [table_name]

| Field | Type | Purpose |
|-------|------|---------|
| id | Integer PK | |
| profile_id | FK → profiles | |
| ... | ... | ... |

### New Enum Values

- [field]: add "[value]"

### Migration Notes

[How to handle existing databases — is this additive only or does it require migration?]
```

If no schema changes are needed, state: **"No schema changes required. Uses existing bounty/milestone tables only."**

---

## Section 9: Dependencies (if any)

```markdown
## New Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| ... | ... | ... | ... |
```

If none needed, state: **"No new dependencies required."**

---

## Checklist Before Integration

```markdown
- [ ] Bounties parse: `python -c "import seed_data; print(len(seed_data.BOUNTIES))"`
- [ ] App loads: `python -c "from main import app; print('OK')"`
- [ ] Frontend builds: `cd app/frontend && npm run build`
- [ ] README updated (if milestone/bounty/program counts changed)
- [ ] SBOM updated (if dependencies added)
- [ ] VERSION updated (if this is a release)
- [ ] Reseed tested on existing profile
```
