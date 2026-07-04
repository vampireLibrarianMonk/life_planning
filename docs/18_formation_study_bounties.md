# Formation Study Bounties

## Purpose

Not every learning outcome fits inside a development pillar. Some activities are cross-cutting — they teach civic literacy, moral reasoning, scientific skepticism, caregiving burden, and institutional awareness simultaneously. Forcing them into a single pillar distorts both the pillar and the activity.

Formation Study Bounties are a structured program track for activities that produce **integrated understanding** across multiple pillars. They include books, videos, service placements, simulations, and institutional case studies — all using fact-sheet templates that require the child to extract specific lessons rather than passively consume content.

---

## Core Principle

A bounty is not a report. A fact sheet forces extraction of structure:

- What is the system?
- Who benefits?
- What are the incentives?
- What breaks if this is removed?
- What is the moral lesson?

The child cannot complete the template by summarizing. They must **analyze**.

---

## Bounty Families

### Life Cards & Belonging Maps

Visual-map bounties that help the child understand where their life sits in time and where their responsibilities sit in relation to others.

**Life Chart Card Reflection**

The Life Chart Card itself is a dashboard-level visual map. Optional Formation Study bounties can ask the child to write or discuss one section at a time.

Template fields:
- Life section: Before Conception, Conception to Birth, Childhood & Formation, Adulthood & Responsibility, Death, or After Death / Legacy
- What this section means in plain language
- What I received, am receiving, or will be responsible for
- One family story, historical example, or practical responsibility connected to this section
- One question I should ask my parents, grandparents, mentors, priest/pastor, teacher, or future self
- One-sentence lesson

**Expanding Breadth of Belonging Fact Sheet**

Each ring of the Breadth of Belonging chart can become a bounty.

Religious ring sequence:

```text
Person → Family → Kin / Tribe → Parish → Local Community → Nation → Church → Humanity → God
```

Secular ring sequence:

```text
Person → Family → Kin / Tribe → Local Community → Civic Community → Nation → Civilization → Humanity → Truth / Meaning
```

Template fields:
- Ring name and variant used (religious or secular)
- What this circle means
- What I receive from it
- What I owe to it
- What can corrupt it
- What happens if it is neglected
- One real example
- One family discussion question
- One-sentence lesson

**Recommended bounty category:** `breadth_of_belonging`  
**Recommended program:** Formation Study  
**Reference doc:** `docs/19_life_cards_life_maps.md`

---

### Civic Service Placements

Experiential bounties where the child works within or shadows a civic or labor institution.

**Union / Labor Institution Fact Sheet**

Template fields:
- Union name and trade/industry represented
- Membership structure and eligibility
- Dues structure
- Leadership selection process
- Bargaining role and recent outcomes
- Political activity (endorsements, PAC spending)
- Corruption safeguards (elections, audits, oversight)
- Benefits to workers (wages, safety, representation)
- Risks to workers (dues cost, strike exposure, leadership capture)
- Civic lesson: What does this institution teach about collective power?

**Placement criteria:** Age 13+ for shadowing, 16+ for volunteer/intern service. Parental approval required. Placement is observation and learning, not endorsement.

---

### Jury Duty & Controversial Case Review

Repeatable civic-literacy bounties where the child reviews a controversial court case as if serving as a careful juror. This is not a punditry exercise and not a way to teach the child which public opinion to hold. It teaches fair process when law, evidence, media, politics, public emotion, and moral judgment collide.

**Recommended placement:** Civic pillar → Civic Literacy Bounties → Jury Duty & Controversial Case Review. Large versions also appear under **Summer Capstone Projects**.

**Internal category:** `jury_case_review`  
**Suggested bounty type:** `civic_literacy`  
**Special classification:** `summer_capstone` for the 4–8 week version  
**Repeat rule:** repeatable, including repeat review of the same case at an older maturity level  
**Decay rule:** no decay; in the current seeded bounty model this is represented by `repeatable = 1`, `decay_divisor = 1`, and `reset_days = None`

Core questions:
- What was charged or claimed?
- What did the law require?
- What evidence was admitted?
- What evidence was excluded or unavailable?
- What did each side argue?
- What did the jury or court decide?
- What did the public think happened?
- What did the courtroom record actually show?
- What moral and institutional questions remain?

Required evidence-discipline categories:
- Confirmed fact
- Allegation
- Admitted evidence
- Excluded evidence
- Official finding
- Public narrative
- Speculation
- Personal reaction

Source reliability levels:
1. Direct court record — docket, filing, order, transcript, jury instructions, exhibit, verdict form
2. Official legal record — appellate opinion, sentencing memo, court press release, prosecutor/defense filing
3. Verified primary material — full official trial video, hearing audio, admitted bodycam, official public records
4. Serious secondary source — legal analysis, long-form journalism with documents, law review, court-focused reporting
5. Public narrative / commentary — news clips, edited videos, podcasts, social media, memes, political framing

Short seeded bounty statements:
- **Fairness Story:** Read a simple case story and identify what evidence matters.
- **Controversial Case Fact Sheet:** Identify charges, evidence, verdict, and civic lesson.
- **Public Narrative vs. Court Record:** Compare public claims to what the courtroom record showed.
- **Source Reliability Log:** Rank sources and identify what records are missing.
- **Legal Standard & Jury Instructions:** Translate the relevant standard into plain language.
- **Summer Capstone:** Produce a full packet and family presentation after 4–8 weeks of research.

Full summer capstone outputs:
1. Case summary
2. Case timeline
3. Charges or claims sheet
4. Burden of proof explanation
5. Legal elements sheet
6. Evidence chart
7. Witness credibility notes
8. Source reliability log
9. Full video / transcript availability report
10. Public narrative versus courtroom record comparison
11. Juror conclusion
12. Moral questions remaining
13. Institutional questions remaining
14. Family presentation
15. Final reflection

Guardrails:
- Do not teach mob judgment.
- Do not teach automatic distrust of institutions.
- Do not teach automatic trust in institutions.
- Do not teach partisan identity.
- Do not reward agreement with the parent; reward disciplined process.
- Do not flatten legal and moral questions. A verdict answers a legal question but may not settle every moral or institutional concern.

**Parent discussion prompts:** What did you think before reviewing the case? What changed after reviewing the record? What evidence mattered most? Did the public narrative match the courtroom record? Why does burden of proof matter? What would happen if crowds decided guilt instead of courts? What would happen if courts became immune from criticism? What remains unknown?

---

### Book Study Fact Sheets

Structured reading bounties for books that illuminate systems, community, power, or moral reasoning.

**Template fields (all book studies):**
- Title, author, publication year
- Core argument in 2–3 sentences
- Key evidence or examples cited
- What the book gets right
- What may be overstated or missing
- Lessons for family, civic life, or personal formation
- One question the book raised that you cannot yet answer

**Pre-loaded book studies:**

| Book | Author | Primary Pillar Cross-Links |
|------|--------|---------------------------|
| *Tribe* | Sebastian Junger | Heritage, Civic, Relationships |
| *The Business Secrets of Drug Dealing* | Taibbi / Anonymous | Civic (Shadow Systems), Character |

**Tribe Book Fact Sheet** — additional fields:
- Junger's argument about belonging and shared hardship
- The relationship between war, trauma, and community
- Modern loneliness and social fragmentation
- What lessons apply to military service, family, civic life
- What breaks if community cohesion disappears

**Drug Lord / Criminal Enterprise Book Study** — additional fields:
- How the book describes hierarchy, incentives, secrecy
- Money flow and risk distribution
- Violence, loyalty, and recruitment
- Institutional failures that enable the system
- Civic and moral lessons (not operational instructions)

**Guardrail:** Focus is on recognizing systems, not learning criminal method. The template explicitly excludes operational detail.

---

### Video Breakdown Fact Sheets

Structured viewing bounties that teach the child to separate metaphor, physics, math, speculation, and entertainment.

**Seven Dimensions Video Breakdown**

Template fields:
- Video title, creator, platform, length
- List each "dimension" as presented by the speaker
- For each: Is the claim mathematical, physical, metaphorical, speculative, or unsupported?
- Is the speaker using "dimension" correctly (in the mathematical/physics sense)?
- What is the difference between a spatial dimension, a mathematical abstraction, and a rhetorical device?
- What claims could be tested? What claims cannot be tested?
- Overall assessment: education, entertainment, or misinformation?

**Purpose:** Anti-gullibility training. The internet presents speculation as science. The child must learn to identify which.

---

### Moral Pattern Fact Sheets

Repeatable fact sheets on universal patterns of vice and virtue.

**Seven Deadly Sins — one per sin:**

| Sin | Distorted Desire |
|-----|-----------------|
| Pride | Disordered self-regard |
| Greed | Disordered acquisition |
| Lust | Disordered appetite |
| Envy | Disordered comparison |
| Gluttony | Disordered consumption |
| Wrath | Disordered anger |
| Sloth | Disordered rest |

**Deadly Sin Fact Sheet Template:**
- Define the sin
- Describe its distorted desire (what good thing does it corrupt?)
- Identify its opposite virtue
- How it appears in: childhood, adulthood, family, money, politics, institutions
- Long-term consequences if it compounds (velocity → acceleration)
- One historical or literary example
- One personal guardrail against this pattern

**Cross-links:** Catholic Formation, Secular Sacred Formation, Character. Also connects to the velocity/acceleration concept — a sin is not merely an isolated act; it can become a trajectory.

---

### Institutional Case Studies

Fact sheets analyzing specific institutional behaviors that reveal how power, access, and narrative interact.

**White House Press Fact Sheet (Matt Taibbi accounts)**

Template fields:
- Event or period described
- Journalists involved
- Official narrative presented
- Incentive structure for the journalists
- Access dynamic (what did proximity cost? what did it buy?)
- What this teaches about government-media relationships
- Main lesson: journalism can become dependent on access to the institutions it is supposed to scrutinize

**General Institutional Case Study Template:**
- Institution name and type
- Official mission vs. observed behavior
- Incentive structure of key actors
- Who benefits from the current arrangement?
- Who is harmed or excluded?
- What oversight exists? Is it functional?
- What would change if this institution disappeared?

---

### Caregiving Simulations

Experiential bounties that teach the burden, patience, and schedule disruption of caregiving — before the child has a real dependent.

**Caregiving Simulation Program**

Structure: 72-hour continuous simulation using a programmable infant doll (e.g., RealCare Baby) or equivalent.

Tracking fields:
- Feeding events (count, timing, duration)
- Changing events
- Soothing events (what worked, what didn't)
- Sleep interruptions (count, duration, recovery time)
- Safety checks
- Emotional response journal (frustration, tenderness, boredom, resentment)
- Schedule disruption (what did you have to cancel or delay?)
- Reflection: What is the difference between liking children and being responsible for one?

**Age band:** 13–18 (Formation phase). Cross-links to Life Skills, Relationship Discernment, Family Economy, Inheritance & Stewardship.

**Purpose:** Parenthood is not an aesthetic. It is duty under fatigue. The child should experience the weight before making irreversible decisions.

---

## Integration with Existing System

These bounties live under the **Formation Study** program in the Programs & Economy section. They do not create new pillars. They use the existing bounty infrastructure (tiers, repeatable/one-time, decay, streaks) and cross-link to relevant pillars through milestone tagging.

**Suggested tier assignments:**
- Life Chart Card Reflections: Bronze+ (accessible as family discussion; can deepen with age)
- Breadth of Belonging Rings: Bronze through Platinum+ (early rings are concrete; later rings require institutional and moral synthesis)
- Civic Service Placements: Gold+ (requires demonstrated responsibility)
- Jury Duty & Controversial Case Review: Bronze through Diamond (early fairness stories through full summer capstone)
- Book Studies: Silver+ (requires reading ability and analytical writing)
- Video Breakdowns: Silver+ (requires critical thinking)
- Moral Pattern Fact Sheets: Bronze+ (accessible at entry level, repeatable)
- Institutional Case Studies: Gold+ (requires contextual knowledge)
- Caregiving Simulations: Silver+ (requires physical responsibility)

**Seeded Life Cards / Belonging reward schedule:**

| Bounty family item | Tier | Base reward | Decay / reset |
|---|---:|---:|---|
| Life Chart section reflection | Bronze | $1.50 | halves; resets after 14 days |
| Person / Family ring | Bronze | $1.00 | halves; resets after 14 days |
| Kin / Parish / Local Community ring | Silver | $2.00 | halves; resets after 21 days |
| Civic / Nation / Church ring | Gold | $3.00 | thirds; resets after 30 days |
| Civilization / Humanity / God / Truth-Meaning ring | Platinum | $5.00 | thirds; resets after 45 days |
| Whole-map teaching synthesis | Diamond | $8.00 | quarters; resets after 90 days |
| Jury fairness story | Bronze | $10.00 | no decay; repeatable |
| Controversial case fact sheet | Gold | $50.00 | no decay; repeatable |
| Public narrative vs. court record | Gold | $60.00 | no decay; repeatable |
| Source reliability log | Platinum | $75.00 | no decay; repeatable |
| Legal standard / jury instructions | Platinum | $100.00 | no decay; repeatable |
| Jury Duty summer capstone | Diamond | $500.00 | no decay; repeatable |
| Teach a family case discussion | Diamond | $150.00 | no decay; repeatable |

---

## Relationship to Existing Programs

This program complements but does not replace:
- **Research Bounties** (saint/paradox/effect fact sheets) — those are narrower templates
- **311 Civic Service** — that is municipal engagement; this includes broader institutional literacy
- **Catholic Practices** — the deadly sins sheets connect but are not devotional practice
- **Life Maps dashboard cards** — those are visual overviews; Formation Study bounties turn selected map sections and belonging rings into concrete learning tasks
- **Civic, Economic & Institutional Navigation** — jury case review teaches court records, burden of proof, public narrative discipline, and institutional accountability without mob behavior

Formation Study Bounties are the "liberal arts laboratory" of the system — cross-cutting, analytical, and designed to produce a person who can read institutions, narratives, and moral patterns without being captured by any of them.
