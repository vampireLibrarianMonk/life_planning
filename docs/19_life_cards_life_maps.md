# Life Cards & Life Maps

## Purpose

Life Cards are dashboard-level formation maps. They help the child see the shape of a human life and the widening circle of responsibility that comes with maturity.

They are not meant to replace development pillars, milestones, or bounties. They are the visual frame that helps those existing structures make sense:

```text
I inherited something.
I am becoming someone.
I belong to widening circles.
I will leave something behind.
```

The app currently treats these as **Life Maps** on the profile dashboard.

---

## 1. Life Chart Card

### Internal name

```text
life_chart_card
```

### App type

```text
visual_dashboard_card
```

### Purpose

The Life Chart Card shows the whole arc of human life:

```text
Before Conception → Conception to Birth → Childhood & Formation → Adulthood & Responsibility → Death → After Death / Legacy
```

Its job is to teach that a child did not appear out of nowhere, is not merely waiting for adulthood, and will leave consequences behind.

### Core teaching

Use this child-facing summary:

```text
You came from a story that started before you.
You are living your part of the story now.
One day, others will inherit what you helped build, repair, protect, or damage.
```

### Sections

| Section | Child-facing question | Formation connection |
|---|---|---|
| Before Conception | What world was prepared before I arrived? | Heritage, inheritance, civic conditions, family story |
| Conception to Birth | What did others give before I could give anything back? | Human worth before productivity, dependence, protection |
| Childhood & Formation | What kind of person am I becoming? | Body, mind, faith/meaning, character, relationships, skills |
| Adulthood & Responsibility | What responsibilities become mine? | Vocation, family, stewardship, service, civic duty |
| Death | What should be repaired, preserved, or entrusted before death? | Reconciliation, estate, records, memory, spiritual questions |
| After Death / Legacy | What will others inherit because I lived? | Children, students, institutions, wealth/debt, traditions, harm repaired or transmitted |

### Cross-links

- Dimensional Thinking / Life Navigation
- Heritage & Identity
- Inheritance, Burden & Stewardship
- Catholic Formation
- Secular Sacred Formation
- Character
- Financial Development
- Civic & Institutional Navigation
- Life Skills

---

## 2. Expanding Breadth of Belonging

### Internal name

```text
breadth_of_belonging
```

### App type

```text
visual_board + formation_study_bounty_series
```

### Purpose

This map teaches that responsibility widens as vision widens:

```text
As our vision expands beyond the self, our responsibilities and sense of belonging widen.
```

It can be taught through either a religious or secular vocabulary without changing the underlying formation principle.

### Religious ring order

```text
Person → Family → Kin / Tribe → Parish → Local Community → Nation → Church → Humanity → God
```

### Secular ring order

```text
Person → Family → Kin / Tribe → Local Community → Civic Community → Nation → Civilization → Humanity → Truth / Meaning
```

### Why this belongs in Formation Study Bounties

The Breadth of Belonging chart is a visual board, but the learning happens through repeated fact-sheet work. Each ring can become a bounty that asks the child to explain:

- what this circle gives me
- what I owe to it
- what corrupts it
- what happens if it is neglected
- one real example
- one family discussion question
- one sentence lesson

This makes it a natural family under the existing **Formation Study Bounties** program.

---

## 3. Recommended Bounty Program Integration

### Program

```text
Formation Study
```

### Program key

```text
formation_study
```

### Bounty family category

```text
breadth_of_belonging
```

### Suggested variants

```text
religious
secular
```

### Suggested bounty metadata

Use existing bounty fields rather than creating a new table:

| Field | Recommended use |
|---|---|
| `category` | `breadth_of_belonging` |
| `pillar` | optional cross-linked pillar such as `dimensional_navigation`, `civic`, `heritage`, `catholic_formation`, or `secular_sacred_formation` |
| `title` | `Breadth of Belonging: Person`, `Breadth of Belonging: Family`, etc. |
| `description` | ring meaning and variant notes |
| `requirements` | fact-sheet template requirements |
| `criteria` | what makes the explanation complete |
| `reference` | `/reference_images/expanding_breadth_religious.png` or `/reference_images/expanding_breadth_secular.png` |
| `tier` | Bronze/Silver for early rings, Gold+ for civic/institutional rings |
| `age_band` | usually `6-12` for simple circles, `13-18` for institutional/civilizational analysis |

---

## 4. Universal Breadth of Belonging Bounty Template

```markdown
# Breadth of Belonging Bounty

## Ring

Person / Family / Kin / Parish / Local Community / Nation / Church / Humanity / God

or

Person / Family / Kin / Local Community / Civic Community / Nation / Civilization / Humanity / Truth-Meaning

## What This Circle Means

Explain this circle in simple words.

## What I Receive From It

What does this circle give me?

Examples: care, protection, language, law, worship, education, opportunity, identity, belonging.

## What I Owe To It

What responsibilities do I have toward this circle?

Examples: honesty, respect, service, gratitude, repair, participation, protection of others, stewardship.

## What Can Corrupt It

What can make this circle unhealthy?

Examples: selfishness, tribalism, neglect, abuse, corruption, arrogance, forgetting history, blind obedience.

## What Happens If It Is Neglected

What happens when people stop caring about this circle?

## One Real Example

Give one example from family, history, current events, faith, school, local life, or personal experience.

## One Family Discussion Question

Write one question the family should discuss together.

## One-Sentence Lesson

Summarize the lesson in one sentence.
```

---

## 5. Suggested Bounty Series

### Religious version

1. Person
2. Family
3. Kin / Tribe
4. Parish
5. Local Community
6. Nation
7. Church
8. Humanity
9. God

### Secular version

1. Person
2. Family
3. Kin / Tribe
4. Local Community
5. Civic Community
6. Nation
7. Civilization
8. Humanity
9. Truth / Meaning

### Tier guidance

| Ring type | Suggested tier | Reason |
|---|---:|---|
| Person / Family | Bronze | Accessible, concrete, family-centered |
| Kin / Local / Parish | Silver | Requires memory, observation, and explanation |
| Civic / Nation / Church | Gold | Requires institutional literacy |
| Civilization / Humanity / God / Truth-Meaning | Platinum+ | Requires abstraction, humility, and synthesis |

### Seeded repeatable bounties

The app seeds the following repeatable bounties for new profiles and can add them to existing profiles through the profile reseed endpoint. Rewards are intentionally modest and decay so repetition reinforces learning without creating runaway payouts.

| Seeded bounty | Tier | Base reward | Decay | Reset window | Scaling expectation |
|---|---:|---:|---:|---:|---|
| Life Chart Reflection: One Life Section | Bronze | $1.50 | ÷2 | 14 days | One section, one concrete family/personal implication |
| Breadth of Belonging: Person or Family Ring | Bronze | $1.00 | ÷2 | 14 days | Simple household-level explanation |
| Breadth of Belonging: Kin, Parish, or Local Community Ring | Silver | $2.00 | ÷2 | 21 days | Real example beyond self; asks/observes another person |
| Breadth of Belonging: Civic, Nation, or Church Ring | Gold | $3.00 | ÷3 | 30 days | Institutional literacy: benefits, duties, incentives, failure modes |
| Breadth of Belonging: Civilization, Humanity, God, or Truth-Meaning Ring | Platinum | $5.00 | ÷3 | 45 days | Abstract synthesis across at least two pillars and one real-world consequence |
| Life Maps Synthesis: Teach the Whole Map | Diamond | $8.00 | ÷4 | 90 days | Teaches both maps, answers questions, names possible misunderstandings |

The decay divisor means that repeated completions before reset are reduced. For example, a $3.00 Gold bounty with `decay_divisor = 3` pays $3.00, then $1.00, then $0.33, then bottoms out according to app rules until the reset window passes.

---

## 6. Guardrails

- The Life Chart Card should not be turned into a coercive doctrine test.
- The after-death section should distinguish worldview literacy from forced belief.
- The Breadth of Belonging series should widen responsibility without erasing legitimate local duties.
- The child should learn that family, tribe, nation, church, civilization, humanity, truth, and God can each be misunderstood or corrupted if separated from conscience, humility, and responsibility.
- The maps are formative: they show the child where their life sits in time and where their duties sit in relation to others.
