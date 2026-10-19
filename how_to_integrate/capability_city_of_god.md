# City of God: Augustinian Spiritual Warfare
## An interior-formation program that teaches a child Augustine's two cities and two loves — to recognize when their own loves are out of order and when the Accuser is at work, and to build the sacramental defenses that keep them free.

> Augustinian warfare, Track B of 2. Sibling to `capability_just_war.md` (Track A).
> Track A trains the OUTWARD judgment ("Is THIS use of force just?"). This program trains the
> INWARD defense ("Are MY loves in order, and am I being accused or tempted?"). It EXTENDS the
> existing `docs/07_spiritual_warfare_discernment.md` rather than duplicating it.

---

## Placement

**Program:** New program: **City of God**
**Category:** `city_of_god`
**Pillar(s):** Primary `spiritual`; cross-tagged `catholic_formation` (Reconciliation / examination of conscience) and `character` (humility, repentance)
**Age bands:** 6-12 (two cities, naming loves), 13-18 (ordering loves, spotting the Accuser), 18-25 (defending relationships), 25-35 (teaching / household rhythm)

New program definition:
- Program key: `city_of_god`
- Program icon: 🏰
- Program description (one sentence): "Learn Augustine's two cities and two loves, recognize disordered love and the Accuser's tactics in your own heart, and build the sacramental defenses that keep you free."
- Phase labels (tier → phase name):
  - `bronze`: "Phase 1: Two Cities, Two Loves"
  - `silver`: "Phase 2: Ordering My Loves (Ordo Amoris)"
  - `gold`: "Phase 3: Spotting the Accuser"
  - `platinum`: "Phase 4: Defending the Rungs"
  - `diamond`: "Phase 5: Guard the House"

---

## What This Adds

- [x] Bounties: 8 (all category `city_of_god`)
- [ ] Milestones: 0
- [x] New program: yes (`city_of_god`)
- [ ] Schema changes: no — uses existing bounty tables only
- [ ] New dependencies: no
- [ ] New routes: no
- [x] New reference doc: `docs/31_augustinian_spiritual_warfare.md` (to be written alongside integration)

---

## Relationship to `docs/07_spiritual_warfare_discernment.md` — EXTEND, DO NOT DUPLICATE

`docs/07` already supplies, and this program **reuses as a given**:
- The Accuser's projection / transference mechanism.
- The conviction-vs-accusation diagnostic (God convicts to heal; the Accuser shames to destroy).
- The sacramental ladder (individual → marriage → family → community → nation → humanity) with per-level attack and defense.

This program adds the specifically **Augustinian** layer that `docs/07` does not develop:
- **The two cities / two loves** (*City of God*, Bk XIV): "two loves built two cities — love of self to the contempt of God built the earthly city; love of God to the contempt of self built the heavenly." The citizenship test is *what* you love and *in what order*.
- **Ordo amoris (rightly ordered love)**: sin is not loving bad things; it is loving real goods in the wrong *order* or *amount* — a lesser good above a greater one, or anything above God. This is the diagnostic engine added on top of `docs/07`'s conviction/accusation test.
- **The restless heart** (*Confessions*): "our heart is restless until it rests in Thee" — disordered love as the root of the interior war.

So: `docs/07` = "who is attacking and how to tell God's voice from the Accuser's." This program = "what are MY loves, are they in order, and how do the sacraments re-order them." They interlock; they do not overlap.

**End goal:** the child can (1) name their own loves and detect disorder, (2) catch the Accuser's projection / accusation / isolation / despair tactics in their own interior life and relationships, and (3) deploy the sacramental ladder defenses in order, starting with themselves.

---

## Bounty Definitions

```python
{
    "tier": "bronze",
    "title": "My Loves List",
    "description": "List the things you love and put them in order, then talk with a parent about whether the order is right.",
    "requirements": "List the things you love — people, activities, possessions, God. Put them in order of how much you love them. Then talk with a parent about whether that order is the right one, and name at least one love that is out of order.",
    "criteria": "Complete for an honest list that includes at least one admitted out-of-order love (e.g., a game loved more than a sibling). Reject a performance of 'I love God most' offered with no real thought.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 2000,
    "pillar": "spiritual",
    "age_band": "6-12",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 90,
},
{
    "tier": "bronze",
    "title": "Two Cities in One Day",
    "description": "At the end of a day, name one choice that pointed toward love of self above all and one that pointed toward love of God and others.",
    "requirements": "At day's end, name one specific choice that pointed toward the 'earthly city' (love of self above all) and one that pointed toward the 'heavenly city' (love of God and others).",
    "criteria": "Complete for specific real moments from the day, not generic statements.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 2000,
    "pillar": "spiritual",
    "age_band": "6-12",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "silver",
    "title": "Ordo Amoris Audit",
    "description": "Identify one genuinely good thing you love out of order, take one concrete step to reorder it, and report what happened.",
    "requirements": "Identify one genuinely GOOD thing you love out of order — status, approval, a relationship, comfort, a device — good in itself but wrong in rank or amount. Take one concrete step to reorder it. Report what happened.",
    "criteria": "Complete when the loved thing is a real good (not an obvious vice), the disorder is correctly diagnosed as wrong rank/amount, and an actual step with an outcome is logged. Reject 'I have no disordered loves.'",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 2500,
    "pillar": "spiritual",
    "age_band": "13-18",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "silver",
    "title": "Restless Heart Journal",
    "description": "Track one craving or restlessness over a week and trace what it is really reaching for.",
    "requirements": "For one week, track one recurring craving or restlessness. Each time, trace past the surface want to the deeper good it is actually reaching for. Connect it to ordo amoris at the end.",
    "criteria": "Complete when the journal moves past the surface want to the deeper good and connects it to rightly ordered love.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 2500,
    "pillar": "spiritual",
    "age_band": "13-18",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 1,
    "reset_days": 365,
},
{
    "tier": "gold",
    "title": "Catch the Accuser",
    "description": "Document a real moment of self-accusation or despair and run the conviction-vs-accusation diagnostic on it.",
    "requirements": "Document a real moment of self-accusation or despair. Run the docs/07 diagnostic: Is this conviction (specific, leads to repair) or accusation (vague, leads to paralysis)? Whose problem is being projected? Does it move me toward communion or isolation? Is it driving me away from the sacraments? Then name the truthful response.",
    "criteria": "Complete when the docs/07 questions are applied explicitly to a REAL interior moment and healthy guilt is distinguished from shame. Reject invented or purely hypothetical cases.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 3000,
    "pillar": "spiritual",
    "age_band": "13-18",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 30,
},
{
    "tier": "gold",
    "title": "Am I the Accuser?",
    "description": "Identify one time you projected your own wound onto someone else and made them the enemy — then make it right.",
    "requirements": "Identify one real time you took your own unreconciled wound and projected it onto someone else (a sibling, parent, friend, or group), making that person the enemy. Then make it right with a concrete act of repair.",
    "criteria": "Complete for honest self-implication (this is the hard half of the docs/07 mechanism) plus an actual act of repair. Reject answers that only catch OTHERS accusing.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 3000,
    "pillar": "spiritual",
    "age_band": "13-18",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 2,
    "reset_days": 90,
},
{
    "tier": "platinum",
    "title": "Hold the Rung",
    "description": "In a real strained relationship, apply the sacramental ladder defense: refuse isolation, name the projection, stay in communion.",
    "requirements": "In a real strained relationship, apply the ladder defense over a defined window: refuse isolation, name the projection when it appears, stay in communion (and, where applicable, return to Reconciliation / Eucharist per docs/07). Log the attack pattern and the defense you used.",
    "criteria": "Complete for a real relationship with real sustained action and a demonstrated refusal to isolate, with outcomes — not a one-time apology.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 5000,
    "pillar": "spiritual",
    "age_band": "18-25",
    "category": "city_of_god",
    "repeatable": 1,
    "decay_divisor": 1,
    "reset_days": 180,
},
{
    "tier": "diamond",
    "title": "Guard the House",
    "description": "Build and run an interior-defense rhythm for a household or mentee group, and teach others to run it alone.",
    "requirements": "Build and run an interior-defense rhythm for a household or mentee group (examination of conscience, naming disordered loves, the conviction-vs-accusation check). Teach others to run it without you.",
    "criteria": "Complete when others can self-diagnose a disordered love and catch an accusation unaided afterward, and a durable household practice exists. Capstone of the program.",
    "reference": "docs/31_augustinian_spiritual_warfare.md",
    "reward_amount": 15000,
    "pillar": "spiritual",
    "age_band": "25-35",
    "category": "city_of_god",
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

- Do **not** turn this into demon-spotting behind every person who annoys the child. The Accuser's signature move is to get *you* to accuse — so the program requires honest self-implication, never only diagnosing others.
- Do **not** reward performed piety ("I love God most") offered without real self-examination.
- Reject completions built on invented or hypothetical interior moments where a real one is required.
- Echo `docs/13`: honor without blindness, faith without coercion, examined faith over checkbox holiness.
- The whole Augustinian point: the sword saves no soul, and the only enemy you are guaranteed to meet is the disorder in your own heart.

---

## Reward Budget

**Target total (completable once per tier, pre-decay):** $35.00 (bronze+silver+gold tiers) + $50 platinum + $150 diamond.

| Tier | Bounties | Subtotal (pre-decay) |
|------|----------|----------------------|
| Bronze | 2 | $40.00 |
| Silver | 2 | $50.00 |
| Gold | 2 | $60.00 |
| Platinum | 1 | $50.00 |
| Diamond | 1 | $150.00 |
| **Total (one each)** | **8** | **$350.00** |

Mirrors Track A's budget for symmetry. Restless Heart Journal and Hold the Rung use `decay_divisor: 1` (no decay) to reward sustained annual/relational practice.

---

## Cross-References

- **`docs/07_spiritual_warfare_discernment.md`**: the parent framework. This program cites it for the Accuser mechanism, the conviction/accusation diagnostic, and the sacramental ladder, and adds ordo amoris + two cities on top.
- **Track A — Just War (`capability_just_war.md`)**: the outward sibling. Augustine insisted the outer war is never rightly judged by someone whose inner loves are disordered — so this program is the integrity check on Track A. State the bridge in both intros.
- **Catholic Formation (`docs/13`)**: Reconciliation and examination-of-conscience actions reuse docs/13 practices; tag these bounties `catholic_formation` as well as `spiritual` so they count in both pillars.
- **Ten Commandments Formation (`ten_commandments`)**: ordo amoris maps onto the 1st commandment (no idol / nothing loved above God) and the "hidden violation becomes a leash" operational-security theme (a disordered love is leverage).
- **Character pillar**: humility and repentance.

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
- [ ] `programs.py` updated with `city_of_god` program
- [ ] `program_phases.py` updated with `city_of_god` phases
- [ ] Reference doc `docs/31_augustinian_spiritual_warfare.md` written
- [ ] README program table + counts updated
- [ ] Reseed tested on existing profile
