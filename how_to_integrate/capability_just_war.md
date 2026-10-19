# Just War Ethics
## A discernment program that teaches a child to judge whether any use of force — from a nation's war to a playground fight to an online pile-on — is actually just, and to refuse when it is not.

> Augustinian warfare, Track A of 2. Sibling to `capability_city_of_god.md` (Track B).
> Augustine gave the West two "warfare" vocabularies that are constantly confused. This program
> trains the OUTWARD judgment ("Is THIS use of force just?"). Track B trains the INWARD defense
> ("Are MY loves in order?"). They interlock: a verdict reached while a disordered love is active
> is suspect, so Track B is the integrity check on Track A.

---

## Placement

**Program:** New program: **Just War Ethics**
**Category:** `just_war`
**Pillar(s):** Primary `civic`; cross-tagged in framing to `character` (restraint, fairness)
**Age bands:** 6-12 (plain-language), 13-18 (full checklist on real cases), 18-25 (lived application + refusal), 25-35 (teaching)

New program definition:
- Program key: `just_war`
- Program icon: ⚖️
- Program description (one sentence): "Learn the disciplined checklist that decides whether any use of force is just — and practice saying no when it is not."
- Phase labels (tier → phase name):
  - `bronze`: "Phase 1: The Rules of a Fair Fight"
  - `silver`: "Phase 2: Judging Real Cases"
  - `gold`: "Phase 3: Both Sides of the Table"
  - `platinum`: "Phase 4: Living It — Refusal & Restraint"
  - `diamond`: "Phase 5: Teach the Checklist"

---

## What This Adds

- [x] Bounties: 8 (all category `just_war`)
- [ ] Milestones: 0
- [x] New program: yes (`just_war`)
- [ ] Schema changes: no — uses existing bounty tables only
- [ ] New dependencies: no
- [ ] New routes: no
- [x] New reference doc: `docs/30_augustinian_just_war.md` (to be written alongside integration)

---

## The Doctrine This Program Teaches

The whole program is built on one checklist. State it in the reference doc and in Phase 1 in plain language.

**JUS AD BELLUM — may we resort to force?**
1. **Just cause** — defense against real, grave, lasting harm; not pride, revenge, or gain.
2. **Legitimate / competent authority** — the right person or body decides, not a self-appointed avenger.
3. **Right intention** — aiming at peace and the restoration of justice, not domination or hatred.
4. **Proportionality** — the good expected must outweigh the evils and disorders produced.
5. **Probability of success** — not futile destruction.
6. **Last resort** — all peaceful means genuinely exhausted.

**JUS IN BELLO — how may force be waged?**
- **Discrimination / distinction** — combatants may be targeted; noncombatants may not.
- **Proportionality of means** — no more force than the objective requires.
- **No intrinsically evil means** — nothing wrong in itself (targeting innocents, torture, terror) is ever licensed by a good cause.

Sources to cite: Augustine, *Contra Faustum* XXII; Aquinas, *Summa Theologiae* II-II q.40; *Catechism of the Catholic Church* §2309; and the secular parallel in International Humanitarian Law / the Geneva Conventions (so the child sees the same logic in both Catholic and civil law).

**End goal:** the child can take ANY conflict — a historical war, a specific modern conflict, a schoolyard escalation, an online dogpile, an institutional crackdown — run the checklist, and reach a defensible verdict with reasons, **including "this fails the test, so no."**

---

## Bounty Definitions

```python
{
    "tier": "bronze",
    "title": "The Playground Just-War Audit",
    "description": "Take one real conflict you witnessed or were part of and run the six just-war questions on it.",
    "requirements": "Pick one REAL conflict (recess, siblings, a game, a group chat). Answer the six jus ad bellum questions in your own words: Was there real harm? Was the right person deciding? Was anyone trying for peace? Was the response proportionate? Could it actually work? Was everything else tried first? Then state what a just response would have been.",
    "criteria": "Complete only for a specific real incident with the child's own reasoning on each question, AND including at least one case where the honest verdict is 'I/we were not justified.' Reject hypotheticals and all-self-justifying answers.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 2000,
    "pillar": "civic",
    "age_band": "6-12",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "bronze",
    "title": "Say It Back: The Rules of a Fair Fight",
    "description": "Recite the six just-war questions and the three rules of how force may be used, in your own words, with an everyday example for each.",
    "requirements": "In your own words, state the six jus ad bellum questions (just cause, right authority, right intention, proportionality, chance of success, last resort) and the three jus in bello rules (protect noncombatants, use no more force than needed, never do an evil act for a good cause). Give one everyday example for each.",
    "criteria": "Complete when the child demonstrates meaning, not memorized definitions — each rule paired with a real example in the child's own language.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 2000,
    "pillar": "civic",
    "age_band": "6-12",
    "category": "just_war",
    "repeatable": 0,
    "decay_divisor": None,
    "reset_days": None,
},
{
    "tier": "silver",
    "title": "Case File: One Historical Conflict",
    "description": "Pick one documented conflict, gather sources from more than one perspective, and score it against every just-war criterion.",
    "requirements": "Choose one documented conflict. Gather sources from more than one perspective. Produce a verdict sheet scoring every jus ad bellum and jus in bello criterion with evidence. Separate confirmed fact from claim. Reach a reasoned verdict — including where a side with a just cause still used unjust means.",
    "criteria": "Complete when sources are cited, fact is separated from claim, and a reasoned verdict is reached. Reject verdicts that score a 'home team' as perfect on every criterion.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 2500,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "silver",
    "title": "Online Pile-On Autopsy",
    "description": "Analyze one real public online pile-on using the just-war checklist.",
    "requirements": "Pick one real, named public online pile-on. Ask: Who appointed themselves the authority? Was the response proportionate to the offense? Was it a last resort? Did it hit noncombatants or bystanders (family, employers, uninvolved people)? Write your verdict with reasons.",
    "criteria": "Complete when the analysis names a concrete real incident and explicitly applies distinction (were uninvolved people harmed?) and proportionality. Reject vague 'the internet is mean' answers.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 2500,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "gold",
    "title": "Steelman Both Sides",
    "description": "Take a contested conflict and write the strongest honest case for each side before giving your verdict.",
    "requirements": "Choose a contested case. Write the strongest honest argument for EACH side — strong enough that a partisan of that side would accept it as fair. Only then render a verdict using the just-war criteria.",
    "criteria": "Complete when both steelmans are genuinely fair (not strawmen) and the verdict follows from the criteria rather than from which side the child prefers. Reject strawmanning.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 3000,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 90,
},
{
    "tier": "gold",
    "title": "Just Cause, Unjust Means",
    "description": "Find a real case where the cause was arguably just but the means violated the rules of how force may be waged.",
    "requirements": "Find and document a real case where the cause was arguably just but the means broke jus in bello (targeting civilians, grossly disproportionate force, or an intrinsically evil act). Explain the two judgments separately.",
    "criteria": "Complete when the child correctly separates the justice of the cause from the justice of the means and explains why a good cause never licenses an evil means.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 3000,
    "pillar": "civic",
    "age_band": "13-18",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 90,
},
{
    "tier": "platinum",
    "title": "The Refusal Log",
    "description": "Over a set window, log real conflicts you personally faced and the restrained, just response you actually chose.",
    "requirements": "Over a defined window, document real conflicts you personally faced and the restrained or just response you actually chose (de-escalation, walking away, reporting instead of retaliating, proportionate response), with the checklist reasoning for each. Include at least one hard case where restraint cost you something.",
    "criteria": "Complete when real logged incidents with outcomes are submitted, including at least one case where restraint had a real cost. This rewards DOING restraint, not writing about it.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 5000,
    "pillar": "civic",
    "age_band": "18-25",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 1,
    "reset_days": 180,
},
{
    "tier": "diamond",
    "title": "Teach the Checklist",
    "description": "Lead a multi-session walkthrough teaching others to run the just-war analysis on their own cases.",
    "requirements": "Lead a multi-session walkthrough (family, younger kids, or peers) teaching others to run the jus ad bellum and jus in bello analysis on their own cases. Have learners evaluate a fresh case independently afterward.",
    "criteria": "Complete when learners can independently evaluate a fresh case, and the teaching surfaced gaps the teacher then addressed. Capstone of the program.",
    "reference": "docs/30_augustinian_just_war.md",
    "reward_amount": 15000,
    "pillar": "civic",
    "age_band": "25-35",
    "category": "just_war",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 365,
},
```

---

## Milestone Definitions

None. This program adds bounties only.

---

## Guardrails

- Do **not** let this become glorification of violence, enemy-lists, or eagerness for conflict. The just-war criteria exist mainly to say **no** — to restrain, disqualify, and refuse.
- Do **not** reward a verdict that conveniently blesses whatever the child's "home team" already wanted. Every repeatable cycle must include at least one case where the child's own side/choice fails the test.
- Reject completions that score one side as perfect on every criterion, that use hypotheticals where a real case is required, or that strawman the opposing side.
- Reward correct **refusals and restraint** at least as richly as verdicts of justification.
- This is formation, not indoctrination: judgment without bloodlust, fairness without relativism.

---

## Reward Budget

**Target total (completable once per tier, pre-decay):** $82.00
**Repeatable lifetime value:** varies with decay; each repeatable bounty halves per completion (except The Refusal Log, which uses `decay_divisor: 1` = no decay, rewarding sustained lived practice).

| Tier | Bounties | Subtotal |
|------|----------|----------|
| Bronze | 2 | $40.00 |
| Silver | 2 | $50.00 |
| Gold | 2 | $60.00 |
| Platinum | 1 | $50.00 |
| Diamond | 1 | $150.00 |
| **Total (one each)** | **8** | **$350.00** |

(Subtotals reflect per-completion value at full/pre-decay amounts: bronze $20+$20, silver $25+$25, gold $30+$30, platinum $50, diamond $150.)

---

## Cross-References

- **Track B — City of God (`capability_city_of_god.md`)**: the integrity check. A Just War verdict reached while a known disordered love (hatred, tribal pride, revenge) is active is suspect and should be re-run after Track B self-examination. State this explicitly in both program intros.
- **Ten Commandments Formation (`ten_commandments`)**: the Just Cause / no-intrinsically-evil-means bounties cross-link to the 5th commandment study (the limits on killing).
- **Civic Chain of Command (`civic_chain_of_command`) & 311 (`311_civic`)**: the "legitimate authority" criterion links to who actually holds the authority to use force in the child's real city and nation.
- **Jury Duty & Case Review (`jury_case_review`)**: shares the discipline of separating confirmed fact from narrative before judging a conflict. The Case File and Online Pile-On bounties reuse that method.
- **Docs**: `docs/07_spiritual_warfare_discernment.md` (interior counterpart), `docs/10_civic_institutional_navigation.md` (authority/institutions).

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
- [ ] `programs.py` updated with `just_war` program
- [ ] `program_phases.py` updated with `just_war` phases
- [ ] Reference doc `docs/30_augustinian_just_war.md` written
- [ ] README program table + counts updated
- [ ] Reseed tested on existing profile
