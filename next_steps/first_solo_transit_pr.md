# First Solo Transit PR — title + description

**Pre-filled URL:** see PR_URL below (generated at the end of this file).

---

## TITLE

feat(seed): First Solo Transit progression — accompanied + unaccompanied public-transit milestones and bounties

---

## DESCRIPTION

# First Solo Transit — accompanied + unaccompanied progression (life_skills)

Adds the child's first independent public-transportation capability to the
life_skills pillar as a **two-step progression** (matching the Earn-Your-Car
pattern: skill built under supervision, safety net removed on evidence).

## Why this structure (the age question, settled with the research base)

| Age | What the evidence supports |
|---|---|
| 6-7 | Familiar short trips with friends; Japan solo-errand tradition starts ~5-7; German children walk to school alone from ~6-7 |
| 8-9 | Short solo walks on familiar low-traffic routes; Skenazy NYC-subway case was a 9-year-old |
| 9-10 | Independent road-crossing; transit with supervision fading |
| 10-12 | Typical readiness window for unaccompanied transit — executive function (multi-step planning, working memory) consolidates here; Hillman/PSI international CIM comparison shows German/Japanese children gain independent transit mobility ~2-3 years earlier than US/UK children purely from parental norms |
| 12-14 | Unfamiliar networks, multi-transfer trips |

Key facts: no US law sets a minimum transit age (state home-alone laws vary:
IL 14, MD/NC 8, most none); traffic, not strangers, is the real risk driver;
readiness varies more by child + environment than by age.

## What ships

### Step 1 - Transit Apprentice: Plan It, Lead It (Parent Rides Along)
Bronze, \$3.00, age 6-12, **accompanied planned travel** (evidence-supported ~8-10).
The child does everything - chooses the destination, plans the route, buys
fares, navigates, transfers - while the parent rides along as a **silent
safety net** (no navigating, no course correction, intervention only for
safety). Minimum distance: 2 mi / 3 km recommended.

### Step 2 - First Solo Transit: Destination of Your Choice
Silver, \$5.00, age 6-12, **unaccompanied planned travel** (evidence-supported
~10-12 window). States its prerequisite explicitly: Transit Apprentice
completed + parent readiness judgment (readiness depends on the child, route
complexity, and the local system). Minimum distance: 3 mi / 5 km recommended.
Full check-in protocol: departure, arrival, pre-return.

### Milestones
Two life_skills milestones (6-12, Exploration) mirror the progression:
accompanied planned transit trip, then first solo trip.

## Bounty requirements (what the child must do)
1. Destination of THEIR choosing (library, store, park, museum) - not an
   assigned errand
2. Full route planning by the child: line/bus, transfers, fare cost, timing,
   backup plan for missed connections
3. The round trip: own fare, right vehicle, transfers, there and back
4. Check-in protocol: departure, arrival, pre-return
5. Evidence: route plan, fare receipt/card, destination photo, trip report
   (one surprise, one near-mistake, one thing to do differently)
6. Parent confirms the minimum distance was met and (for solo) that no adult
   accompanied the trip

## Verification

- seed_data.py imports cleanly; 211 bounties total; new entries asserted
  (tier/pillar/age_band/reward/requirements/criteria)
- Full backend suite: 139 passing; ruff check + format clean
- Existing profiles pick these up via the Sync Milestones & Bounties button

## Design notes

- Placed in the independence gap between Organization (6-12) and Driving
  (13-18) in the life_skills milestone ladder
- Minimum distance is parent-configurable (recommended defaults in the text),
  since the right distance depends on the local transit system and neighborhood
- Silver/\$5.00 calibration matches comparable independence events (Change a
  Tire = \$5.00)
- Natural follow-on (not in this PR): a 13-18 Transit Commuter bounty for
  regular independent multi-modal transit use

## PR_URL

