# Civic Sense & Stewardship of the Commons
## Six new bounties that extend the existing 311 Civic Service program from engaging government to taking direct personal ownership of shared physical space.

> Derived from the transcript `transcripts/Why Indians have ZERO Civic Sense.txt` plus research
> anchors (Hardin 1968 + Ostrom; Wilson & Kelling 1982; Peck et al. 2021). These ADD TO the
> existing `311_civic` program — no new program is created.

---

## Placement

**Program:** Existing program: **311 Civic Service** (`311_civic`)
**Category:** `311_civic` (existing)
**Pillar(s):** `civic` (existing)
**Age bands:** 6-12 and 13-18

No new program, no new phases. These six bounties nest inside the existing phase arc
(Awareness → Engagement → Service → Leadership) ahead of the Diamond capstone.

**The gap these fill:** every existing 311 bounty engages *government* (reporting, meetings,
budgets, testimony, organizing). None teaches the child to take **direct personal ownership of a
shared physical space** — restore it, maintain it, observe the behavioral ripple. That is exactly
the transcript's thesis (broken windows, endowment effect, be-the-change), and the natural
extension of the program.

---

## What This Adds

- [x] Bounties: 6 (all category `311_civic`)
- [ ] Milestones: 0
- [ ] New program: no (extends existing `311_civic`)
- [ ] Schema changes: no — uses existing bounty tables only
- [ ] New dependencies: no
- [ ] New routes: no
- [x] Optional edit: the Diamond `311 Civic Service Program Complete` capstone criteria updated to reference at least one physical-stewardship completion as evidence (see Guardrails).

---

## The Concepts These Teach (from the transcript + research)

| Concept | Source | What the child actually DOES |
|---------|--------|------------------------------|
| **Broken windows** — visible disorder signals norms are unenforced and invites more | Wilson & Kelling, *The Atlantic*, 1982; transcript's clean-vs-dirty field experiment | Restore a degraded space, observe over 14 days whether it holds |
| **Endowment effect / psychological ownership** — felt ownership drives stewardship | Peck et al., *J. Marketing*, 2021; Japan classroom-cleaning example | "Adopt" one space and maintain it for 8 weeks |
| **Tragedy of the commons** — private benefit, spread cost; self-governance is a third path | Hardin, *Science*, 1968; Ostrom, *Governing the Commons*, 1990 | Map the incentives, test one simple local rule |
| **Enforcement vs. incentivizing bad behavior** | Coldplay moon-glasses queue | (reinforced across bounties) |
| **Be the change / quiet modeling** | Stray-puppy story | Improve a space by example without confronting anyone, observe ripple |
| **Measurable costs** (financial, health, tourism) | Railway theft ₹260cr; 40% plastic on streets; road deaths | Build a local cost ledger |

---

## Bounty Definitions

```python
{
    "tier": "silver",
    "title": "Broken Window Repair: Observe-and-Restore",
    "description": "Find a degraded shared space, restore it yourself, and observe over two weeks whether the restoration holds.",
    "requirements": "Photograph a small neglected shared space (a littered curb, a scuffed stairwell, an overgrown bench). Restore it yourself, safely. Re-photograph. Check it on days 3, 7, and 14 and log whether it stayed clean, degraded again, or others helped maintain it. Write what the pattern tells you about the broken-windows idea.",
    "criteria": "Complete when before/after photos and a 14-day observation log are submitted. Judge the restoration AND the follow-up observation, not a one-time cleanup. Must be a genuinely public/shared space (not the child's own yard or room); photos must show real change; the log must span the full two weeks.",
    "reference": "docs/10_civic_institutional_navigation.md",
    "reward_amount": 1200,
    "pillar": "civic",
    "age_band": "6-12",
    "category": "311_civic",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 60,
},
{
    "tier": "silver",
    "title": "Civic Reporting App Power-User",
    "description": "Become fluent with your municipality's reporting app or portal and route real issues to the right authority with tracking.",
    "requirements": "Install or bookmark your city's reporting app/portal. File 3 reports in different categories, each with correct category, precise location, and a photo. Record each tracking number and which department it routes to. Follow each to resolution or a status update. Note which categories resolved fastest.",
    "criteria": "Complete when 3 correctly-categorized, well-documented reports are filed and tracked. Builds on 'First 311 Report' by requiring category accuracy and routing understanding. Real issues only; frivolous or duplicate reports don't count; must show follow-up status, not just submission.",
    "reference": "docs/10_civic_institutional_navigation.md",
    "reward_amount": 1200,
    "pillar": "civic",
    "age_band": "6-12",
    "category": "311_civic",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "silver",
    "title": "Be the Change: Quiet Modeling",
    "description": "Improve a shared space by quiet example — without confronting or shaming anyone — and observe the ripple.",
    "requirements": "Pick a situation where a shared space is being neglected. WITHOUT speaking to, correcting, or shaming anyone, simply do the right thing visibly (pick up the litter, straighten the chairs, return the carts). Observe and log whether anyone else joined in or whether the space stayed better afterward. Write what you noticed about modeling versus lecturing.",
    "criteria": "Complete when the child documents the quiet action and the observed ripple effect. Judge the modeling and the honest observation (a ripple of zero is a valid result). Explicitly NO confrontation, filming of strangers, or public shaming. Reward the action and observation, never a performance posted for approval.",
    "reference": "docs/10_civic_institutional_navigation.md",
    "reward_amount": 1500,
    "pillar": "civic",
    "age_band": "6-12",
    "category": "311_civic",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 90,
},
{
    "tier": "gold",
    "title": "Adopt-a-Space: Take Ownership (8-Week Steward)",
    "description": "Adopt one specific shared space and take ongoing responsibility for keeping it well for 8 weeks.",
    "requirements": "Choose one shared space you use regularly. Commit to maintaining it for 8 weeks. Keep a dated log of each upkeep visit (what you did, how long). Note anything that changed in how you feel about the space, or how others treat it, by the end.",
    "criteria": "Complete when 8 weeks of dated upkeep logs for a SINGLE space are submitted and the child can describe the shift from 'a public space' to 'my responsibility.' One space sustained over time, not 8 one-off cleanups; gaps longer than ~10 days break the streak; the reflection must be concrete, not slogans.",
    "reference": "docs/10_civic_institutional_navigation.md",
    "reward_amount": 2500,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "311_civic",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 120,
},
{
    "tier": "gold",
    "title": "Tragedy of the Commons Field Study",
    "description": "Document one real shared resource being overused, map the incentives, and test one simple local rule.",
    "requirements": "Identify a shared resource near you that is overused or neglected (a common bin, a shared fridge, a park, a group chat). Observe and document how each user privately benefits from neglecting it while the cost spreads to everyone. Propose ONE simple, non-confrontational local rule or nudge (a sign, a labeled bin, a shared schedule) and, where you have standing to do so, try it. Log whether behavior changed.",
    "criteria": "Complete when the child submits an incentive map plus a documented attempt at a self-governance fix (per Ostrom) with an honest before/after — even if it failed. Analysis must rest on observed evidence, not opinion; the proposed rule must have actually been tried where the child legitimately could, not merely written up.",
    "reference": "docs/10_civic_institutional_navigation.md",
    "reward_amount": 3000,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "311_civic",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 120,
},
{
    "tier": "gold",
    "title": "The True Cost of Low Civic Sense (Local Ledger)",
    "description": "Estimate what neglect of one shared system actually costs your community in money or health.",
    "requirements": "Pick one local shared system (street cleaning, drain maintenance, a public park, transit upkeep). Find real figures where available (a municipal budget line, a news report, an official estimate) and build a simple one-page ledger: what neglect costs, who pays (usually the taxpayer), and the health or safety knock-on effects. Tie it to one thing you can personally stop contributing to.",
    "criteria": "Complete when a sourced one-page cost ledger is submitted with at least one real local figure and a concrete personal commitment. Must use a real LOCAL figure (not the transcript's India numbers copied over); the personal commitment must be a specific behavior, not a slogan.",
    "reference": "docs/10_civic_institutional_navigation.md",
    "reward_amount": 2500,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "311_civic",
    "repeatable": 0,
    "decay_divisor": None,
    "reset_days": None,
},
```

---

## Milestone Definitions

None. This capability adds bounties only.

---

## Guardrails

- Reward **documented action and follow-through** — photos, dated logs, tracking numbers, sourced figures — never posting or virtue-signaling.
- Do **not** require, encourage, or reward confronting, correcting, filming, or shaming strangers. "Be the Change" is explicitly quiet modeling only.
- Decay + reset values force the child to find a **different** space/resource each repeatable cycle rather than farming one spot.
- End-goal framing: the child becomes someone who takes **ownership of shared space rather than outsourcing it** — the endowment effect, operationalized.
- **Optional capstone edit:** the existing Diamond `311 Civic Service Program Complete` bounty currently evidences only government engagement. Consider updating its `criteria` to also require at least one physical-stewardship completion (Adopt-a-Space or Broken Window Repair) as evidence of direct ownership. This is an edit to existing seed data — note the reseed guardrail: the `(category, title)` tuple must NOT change; only `criteria`/`requirements` text may be refreshed.

---

## Reward Budget

| Tier | Bounties | Subtotal (per completion, pre-decay) |
|------|----------|--------------------------------------|
| Silver | 3 | $12 + $12 + $15 = $39.00 |
| Gold | 3 | $25 + $30 + $25 = $80.00 |
| **Total (one each)** | **6** | **$119.00** |

All amounts are in **cents** in `seed_data.py` (1200 = $12.00). Deliberately matched to the existing 311 scale (silver 1200–1500¢, gold 2500–3000¢) so the economy stays balanced.

---

## Cross-References

- **Existing 311 program (`311_civic`)**: these extend it with physical-space stewardship. Civic Reporting App Power-User directly builds on the existing "First 311 Report Filed."
- **Civic pillar / `docs/10_civic_institutional_navigation.md`**: shared voice and anti-gaming posture ("what you did, not what you could do").
- **Social Need / Social Justice Fact Sheets** (existing civic bounties): same "observe → act → document" discipline; these are the physical-infrastructure counterpart to those social-need sheets.
- **Transcript**: `transcripts/Why Indians have ZERO Civic Sense.txt`.
- **Research anchors**: Hardin 1968; Ostrom 1990/1999; Wilson & Kelling 1982; Peck, Kirk, Luangrath & Shu 2021.

---

## Schema Changes

No schema changes required. Uses existing bounty tables only.

---

## New Dependencies

No new dependencies required.

---

## Checklist Before Integration

- [ ] Bounties parse: `python -c "import seed_data; print(len(seed_data.BOUNTIES))"`
- [ ] App loads: `python -c "from main import app; print('OK')"`
- [ ] Frontend builds: `cd app/frontend && npm run build`
- [ ] (Optional) Diamond 311 capstone criteria updated per Guardrails
- [ ] README counts updated
- [ ] Reseed tested on existing profile
