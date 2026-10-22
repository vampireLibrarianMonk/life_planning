"""Public, no-login DEMO endpoints — an anonymized app demonstrator.

Serves a single, entirely FAKE profile ("Alex Example") from in-memory data so
that worldwide/unauthenticated visitors can see how the app works WITHOUT any
real child's data ever being reachable. These routes:
  * require NO authentication,
  * are strictly READ-ONLY,
  * never touch the database or any real profile,
  * expose no private sections (no behavior log, journals, or financial totals).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["demo"])

# --- Static, anonymized demo content (no real PII, never from the DB) --------

_DEMO_PROFILE = {
    "id": 0,
    "name": "Alex Example",
    "date_of_birth": None,  # no DOB — anonymized
    "avatar": None,
    "avatar_original": None,
    "is_demo": True,
}

# A small, representative slice of milestones across a few pillars/age bands.
_DEMO_ENTRIES = [
    {
        "id": 1,
        "pillar": "spiritual",
        "age_band": "6-12",
        "title": "First prayer unprompted",
        "status": "complete",
        "is_milestone": 1,
        "content": "Began a bedtime prayer habit without reminders.",
    },
    {
        "id": 2,
        "pillar": "financial",
        "age_band": "6-12",
        "title": "Opened a savings jar",
        "status": "practicing",
        "is_milestone": 1,
        "content": "Splits allowance into save / spend / give.",
    },
    {
        "id": 3,
        "pillar": "education",
        "age_band": "13-18",
        "title": "Completed first job shadow",
        "status": "in_progress",
        "is_milestone": 1,
        "content": "Shadowed a local veterinarian for a day.",
    },
    {
        "id": 4,
        "pillar": "character",
        "age_band": "6-12",
        "title": "Admitted a mistake honestly",
        "status": "mastered",
        "is_milestone": 1,
        "content": "Owned up to a broken window before being asked.",
    },
    {
        "id": 5,
        "pillar": "life_skills",
        "age_band": "13-18",
        "title": "Cooks a full meal unaided",
        "status": "introduced",
        "is_milestone": 1,
        "content": "Working through a beginner recipe set.",
    },
    {
        "id": 6,
        "pillar": "heritage",
        "age_band": "6-12",
        "title": "Learned a family story",
        "status": "complete",
        "is_milestone": 1,
        "content": "Recorded a grandparent's immigration story.",
    },
]

# A handful of sample bounties WITH dollar amounts (amounts are fine to show;
# only aggregate financial TOTALS are private, and the demo has none).
_DEMO_BOUNTIES = [
    {
        "id": 1,
        "tier": "bronze",
        "title": "Tidy the shared bookshelf",
        "description": "Sort and straighten the family bookshelf.",
        "reward_amount": 200,
        "current_reward": 200,
        "age_band": "6-12",
        "status": "available",
        "repeatable": 0,
        "times_completed": 0,
    },
    {
        "id": 2,
        "tier": "silver",
        "title": "Plan a weekly budget",
        "description": "Draft a simple weekly budget and review it.",
        "reward_amount": 500,
        "current_reward": 500,
        "age_band": "13-18",
        "status": "claimed",
        "repeatable": 0,
        "times_completed": 0,
    },
    {
        "id": 3,
        "tier": "gold",
        "title": "Teach a younger sibling a skill",
        "description": "Prepare and run a 20-minute lesson.",
        "reward_amount": 1500,
        "current_reward": 1500,
        "age_band": "13-18",
        "status": "complete",
        "repeatable": 0,
        "times_completed": 0,
    },
    {
        "id": 4,
        "tier": "diamond",
        "title": "311 Civic Service capstone",
        "description": "Report and follow up on a real community issue.",
        "reward_amount": 50000,
        "current_reward": 50000,
        "age_band": "18-25",
        "status": "available",
        "repeatable": 0,
        "times_completed": 0,
    },
]


@router.get("/profile")
def demo_profile():
    """The anonymized demo profile."""
    return _DEMO_PROFILE


@router.get("/entries")
def demo_entries():
    """Sample milestones across pillars/age bands."""
    return _DEMO_ENTRIES


@router.get("/bounties")
def demo_bounties():
    """Sample bounties with individual dollar amounts (no totals)."""
    return _DEMO_BOUNTIES
