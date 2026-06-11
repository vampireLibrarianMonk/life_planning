# Implementation Notes for Programming LLM

## Goal

Integrate the new markdown documents into the Life Plan Tracker application as new pillars, addenda, milestone sources, and future structured record types.

## Existing Application Pattern

The app already supports:

- Profiles
- Pillars
- Age-banded milestones
- Notes
- Status toggles
- Family economy
- Wishlist
- User roles
- Seeded milestone data from planning documents

The first integration should be lightweight:

1. Add documents to `docs/`.
2. Add new pillar definitions.
3. Add seed milestones from each document.
4. Use existing note/milestone UI.
5. Add structured records later.

## New Pillar Definitions

Suggested pillar records:

```json
[
  {
    "key": "dimensional_navigation",
    "title": "Dimensional Thinking, Perception & Life Navigation",
    "sort_order": 9
  },
  {
    "key": "civic_economic_navigation",
    "title": "Civic, Economic & Institutional Navigation",
    "sort_order": 10
  },
  {
    "key": "scientific_reality_testing",
    "title": "Scientific Method & Reality Testing",
    "sort_order": 11
  },
  {
    "key": "inheritance_burden_stewardship",
    "title": "Inheritance, Burden & Stewardship",
    "sort_order": 12
  },
  {
    "key": "catholic_formation",
    "title": "Catholic Sacramental Formation",
    "sort_order": 13
  },
  {
    "key": "secular_sacred_formation",
    "title": "Secular Sacred Formation & Civilizational Literacy",
    "sort_order": 14
  }
]
```

## Addenda Attachments

Suggested mapping:

```json
{
  "lost_knowledge_corruption_institutional_blindness": {
    "attach_to": ["scientific_reality_testing"],
    "title": "Lost Knowledge, Corrupted Knowledge, and Institutional Blindness"
  },
  "recidivism_forgiveness_forgetting": {
    "attach_to": [
      "catholic_formation",
      "secular_sacred_formation",
      "inheritance_burden_stewardship"
    ],
    "title": "Recidivism, Forgiveness, and Forgetting"
  }
}
```

## Record Types for Future Database Expansion

### NavigationRecord

Fields:

- profile_id
- domain
- dimension
- position
- azimuth
- velocity
- acceleration
- current_forces
- time_horizon
- course_correction_cost
- notes
- review_date

### ExperimentRecord

Fields:

- profile_id
- question
- hypothesis
- domain
- start_date
- end_date
- intervention
- measurement
- expected_result
- actual_result
- lesson_learned
- follow_up_action

### RealityAudit

Fields:

- profile_id
- claim
- source
- evidence_for
- evidence_against
- confidence_level
- what_would_change_mind
- review_date

### PredictionJournal

Fields:

- profile_id
- prediction
- time_horizon
- confidence_level
- reasoning
- outcome
- lesson_learned

### KnowledgeDecayRecord

Fields:

- profile_id
- claim_or_practice
- original_observation
- original_evidence
- original_explanation
- later_modification
- corruption_or_forgetting
- rediscovery_event
- current_confidence
- lesson_learned

### InstitutionalResistanceRecord

Fields:

- profile_id
- claim
- institution
- dominant_theory
- evidence_presented
- reason_for_resistance
- later_outcome
- acceptance_change
- lesson_preserved

### ExtremeHypothesisRecord

Fields:

- profile_id
- hypothesis
- category
- evidence_claimed
- evidence_missing
- confidence_raise_conditions
- confidence_lower_conditions
- charlatan_risk
- serious_inquiry_path
- review_date

### InheritanceLedgerEntry

Fields:

- profile_id
- domain
- asset_or_burden
- source_generation
- evidence
- current_effect
- risk_level
- action_category
- notes

Allowed action categories:

```text
preserve
repair
reject
investigate
transfer
```

### SacramentRecord

Fields:

- profile_id
- sacrament
- date
- parish
- city_state
- celebrant
- certificate_attachment_id
- sponsor_or_godparent
- notes

### FormationEvent

Fields:

- profile_id
- event_title
- age_band
- location
- formation_category
- what_happened
- what_was_learned
- parent_reflection
- child_reflection
- attachment_ids

### SafetyAuthorityNote

Fields:

- profile_id
- situation
- authority_involved
- boundary_principle_taught
- child_understanding
- parent_follow_up
- concern_level
- action_taken

### MoralRepairRecord

Fields:

- profile_id
- event
- who_was_harmed
- responsibility_accepted
- forgiveness_status
- memory_to_preserve
- boundary_required
- repeated_behavior_evidence
- change_evidence_required
- reconciliation_appropriate
- restoration_appropriate
- review_date

## Minimal UI Changes

### Dashboard

Add new pillar cards.

### Pillar View

Use the current milestone grouping by age band.

### Addendum View

If addenda are not yet first-class objects, represent them as categories within the parent pillar.

### Future Dashboard Widgets

Possible future visualizations:

- Navigation board
- Radius of influence ladder
- Claim confidence ladder
- Inheritance balance sheet
- Sacrament record timeline
- Moral repair tracker

## Guardrails for UX Copy

Avoid:

- Making holiness, maturity, or safety look like a simple completion percentage.
- Turning Catholic formation into checkbox spirituality.
- Turning scientific method into scientism.
- Turning inheritance audit into resentment.
- Turning civic literacy into partisan indoctrination.
- Turning forgiveness into unsafe amnesia.

Use language like:

```text
recorded
reviewed
reflected
in progress
requires follow-up
needs evidence
preserve
repair
investigate
```

rather than:

```text
proved holy
fully safe
complete forever
resolved
obedient
```

## First Implementation Pass

1. Add docs.
2. Add pillar keys.
3. Seed milestone titles by age band.
4. Attach all detailed text as document content or notes.
5. Defer custom record tables until after UI validation.
