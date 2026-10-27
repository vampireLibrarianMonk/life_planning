"""Child Development — age-banded developmental objectives (ORIGINAL content).

This is the authoritative template for the "Child Development" dashboard section
(a top-level section at the same level as Life Maps, NOT a pillar). Objectives
are our own original wording of public-domain developmental facts (MedlinePlus/
NIH, WHO, cross-checked AAP) — NOT a reproduction of any proprietary instrument.

Each objective becomes a PillarEntry row at seed time:
  pillar     = "education"  (satisfies the non-null column; UI never shows it there)
  category   = "child_development:<domain_key>"   (family-readable objectives)
  age_band   = the age-group label ("2mo" ... "5yr")
  age_years  = integer MONTHS, used only as a numeric sort key
  title      = the objective text
  is_milestone = 1 ; status defaults to "not_started" (= the "not yet" mark)

Tri-state marks map onto the existing status ladder:
  not yet -> not_started | emerging -> in_progress | practicing -> complete
"""

# Storage constants
CD_PILLAR = "education"  # non-null column filler; never surfaced under this pillar
CD_CATEGORY_PREFIX = "child_development"
CD_PRIVATE_CATEGORY = "child_development_private"

DOMAINS = {
    "social_emotional": "Social & Emotional",
    "communication": "Communication & Language",
    "thinking": "Thinking & Problem-Solving",
    "gross_motor": "Gross Motor",
    "fine_motor": "Fine Motor",
}

# Age groups: label -> months (numeric sort key)
AGE_GROUPS = {
    "2mo": 2,
    "4mo": 4,
    "6mo": 6,
    "9mo": 9,
    "12mo": 12,
    "18mo": 18,
    "24mo": 24,
    "36mo": 36,
    "48mo": 48,
    "60mo": 60,
}

AGE_GROUP_LABELS = {
    "2mo": "~2 Months",
    "4mo": "~4 Months",
    "6mo": "~6 Months",
    "9mo": "~9 Months",
    "12mo": "~12 Months",
    "18mo": "~18 Months",
    "24mo": "~24 Months (2 years)",
    "36mo": "~36 Months (3 years)",
    "48mo": "~48 Months (4 years)",
    "60mo": "~60 Months (5 years)",
}

# Objectives per age group, per domain (original wording — mirrors the reviewed
# corpus in draft_additions/developmental_checkpoints_draft.md).
OBJECTIVES: dict[str, dict[str, list[str]]] = {
    "2mo": {
        "social_emotional": [
            "Begins to smile back when you smile at them (a true social smile).",
            "Briefly calms when picked up, spoken to, or held.",
            "Looks at your face with interest.",
        ],
        "communication": [
            "Makes soft cooing or gurgling sounds.",
            "Turns toward or quiets at a familiar voice.",
            "Startles or reacts to a sudden loud sound.",
        ],
        "thinking": [
            "Watches your face and follows you with their eyes for a moment.",
            "Begins to track a moving object side to side.",
        ],
        "gross_motor": [
            "Lifts their head briefly during tummy time.",
            "Makes smoother movements with arms and legs.",
        ],
        "fine_motor": [
            "Hands are often unclenched rather than tightly fisted.",
            "Brings a hand toward the mouth.",
        ],
    },
    "4mo": {
        "social_emotional": [
            "Smiles on their own to get your attention.",
            "Enjoys playing with people and may cry when play stops.",
            "Mirrors expressions like a smile or frown.",
        ],
        "communication": [
            'Babbles with expression and takes "turns" making sounds with you.',
            "Turns their head toward the sound of your voice.",
            "Uses different cries for different needs.",
        ],
        "thinking": [
            "Follows a moving toy from side to side with their eyes.",
            "Looks at their own hands with interest.",
            "Reaches for a toy they want.",
        ],
        "gross_motor": [
            "Holds their head steady, without support, when held upright.",
            "Pushes up onto elbows/forearms during tummy time.",
            "May roll from tummy to back.",
        ],
        "fine_motor": [
            "Brings hands together and to the mouth.",
            "Grasps a toy placed in their hand and shakes it.",
        ],
    },
    "6mo": {
        "social_emotional": [
            "Knows familiar faces and may begin to notice strangers.",
            "Enjoys looking at themselves in a mirror.",
            "Reacts when someone nearby seems happy or upset.",
        ],
        "communication": [
            'Takes turns making sounds; strings vowels together ("ah," "eh," "oh").',
            "Responds to their name being called.",
            "Makes sounds to show pleasure or displeasure.",
        ],
        "thinking": [
            "Looks around at nearby things with curiosity.",
            "Brings things to the mouth to explore them.",
            "Reaches for and grabs a toy they want.",
        ],
        "gross_motor": [
            "Rolls over in both directions.",
            "Begins to sit with a little support, then briefly on their own.",
            "When on tummy, pushes up on straight arms.",
        ],
        "fine_motor": [
            "Moves a toy from one hand to the other.",
            "Rakes small objects toward themselves.",
        ],
    },
    "9mo": {
        "social_emotional": [
            "May be clingy or wary with unfamiliar people.",
            "Has favorite toys and people.",
            "Responds differently to a gentle vs. stern voice.",
        ],
        "communication": [
            'Understands "no."',
            'Babbles strings of sounds like "mamama," "babababa."',
            "Copies sounds and simple gestures.",
        ],
        "thinking": [
            "Looks for a toy when it is hidden.",
            "Watches the path of something as it falls.",
            "Passes objects smoothly from hand to hand.",
        ],
        "gross_motor": [
            "Sits well without support.",
            "Gets into a sitting position by themselves.",
            'Pulls up to stand and may begin to "cruise."',
        ],
        "fine_motor": [
            "Bangs two objects together.",
            "Begins to pick up small items with thumb and finger.",
        ],
    },
    "12mo": {
        "social_emotional": [
            "Plays back-and-forth games like peekaboo or pat-a-cake.",
            'Waves "bye-bye."',
            "Looks to a familiar adult and checks your face before trying something new.",
            "Gives or shows you a toy just to share it, then often wants it back.",
        ],
        "communication": [
            "Points at something to ask for it or to show you.",
            "Babbles in long strings that rise and fall like real talking.",
            'Uses "mama" or "dada" for the right person.',
            "Can follow a simple request, especially paired with a gesture.",
        ],
        "thinking": [
            "Looks for a toy they watched you hide.",
            "Looks where you point and shares attention on the same thing.",
            "Drops or places an object into a container on purpose.",
            "Copies a simple action they've seen you do.",
        ],
        "gross_motor": [
            '"Cruises" sideways holding on to furniture.',
            "Stands alone for a moment when they let go.",
            "May take first steps (first independent steps commonly emerge later in the second year).",
        ],
        "fine_motor": [
            "Picks up a small item with a refined pincer grasp (thumb + one fingertip).",
            "Points or pokes with one finger.",
            "Finger-feeds themselves small, soft pieces of food.",
        ],
    },
    "18mo": {
        "social_emotional": [
            "Points to show you something interesting.",
            "Hands you a book when they want a story.",
            "May have tantrums and may cling to caregivers in new situations.",
            "Ventures to explore while staying close to a familiar caregiver.",
        ],
        "communication": [
            "Says several single words.",
            'Shakes head "no" and may say "no."',
            "Points to one body part when asked.",
            "Follows a simple 1-step direction without a gesture.",
        ],
        "thinking": [
            "Plays simple pretend, like feeding a doll.",
            "Points to get your attention to something.",
            "Scribbles on their own.",
        ],
        "gross_motor": [
            "Walks on their own.",
            "Begins to walk up steps with help.",
            "Pulls toys while walking.",
        ],
        "fine_motor": [
            "Drinks from a cup (with some spills).",
            "Eats with a spoon, learning.",
            "Stacks a couple of blocks.",
        ],
    },
    "24mo": {
        "social_emotional": [
            "Copies others, especially adults and older children.",
            "Gets excited around other children.",
            "Plays alongside other children rather than directly with them.",
        ],
        "communication": [
            'Says two-word phrases ("more milk," "go outside").',
            "Points to things in a book when named.",
            "Follows simple two-step instructions.",
            "Familiar people can understand much of their speech.",
        ],
        "thinking": [
            "Finds an object even after seeing it hidden under a cover.",
            "Fills and dumps containers over and over.",
            "Plays make-believe.",
        ],
        "gross_motor": [
            "Runs.",
            "Kicks a ball.",
            "Walks up and down a few stairs holding on.",
        ],
        "fine_motor": [
            "Builds a small tower of several blocks.",
            "Scribbles and may imitate a straight line.",
        ],
    },
    "36mo": {
        "social_emotional": [
            "Takes turns in simple games (with reminders).",
            "Shows concern when a playmate is upset.",
            "Separates from caregivers more easily.",
        ],
        "communication": [
            "Speaks in short sentences of 3+ words.",
            "Says their first name and age when asked.",
            "Strangers can understand most of their speech.",
            'Begins asking "why" questions.',
        ],
        "thinking": [
            "Works a toy with buttons, levers, or moving parts.",
            "Does simple puzzles (3-4 pieces).",
            "Plays pretend with dolls, animals, or people.",
        ],
        "gross_motor": [
            "Climbs well and runs easily.",
            "Walks up stairs with one foot per step.",
            "Pedals a tricycle.",
        ],
        "fine_motor": [
            "Turns book pages one at a time.",
            "Copies a circle with a crayon.",
            "Builds a taller tower of blocks.",
        ],
    },
    "48mo": {
        "social_emotional": [
            "Enjoys cooperative play and make-believe with other children.",
            "Would rather play with other children than alone.",
            "Talks about what they like and are interested in.",
        ],
        "communication": [
            "Tells a simple story or recounts part of their day.",
            "Speaks clearly enough for strangers to understand.",
            'Knows some basic grammar rules ("he," "she").',
            "Sings a song or says a short poem from memory.",
        ],
        "thinking": [
            "Names a few colors and some numbers.",
            "Understands the idea of counting.",
            "Begins to grasp time (morning, night, soon).",
        ],
        "gross_motor": [
            "Hops and stands on one foot for a few seconds.",
            "Catches a bounced ball most of the time.",
        ],
        "fine_motor": [
            "Draws a person with a few body parts (roughly two to four).",
            "Uses child-safe scissors with help.",
            "Copies simple shapes like a plus sign and a few uppercase letters.",
        ],
    },
    "60mo": {
        "social_emotional": [
            "Seeks approval from and imitates friends.",
            "Follows rules and takes turns in games.",
            "Shows more independence and may do simple chores.",
        ],
        "communication": [
            "Speaks clearly in full sentences and holds a conversation.",
            "Tells a simple story with a beginning, middle, and end.",
            'Uses future tense ("we will go").',
            "Says their full name and address with help.",
        ],
        "thinking": [
            "Counts 10 or more things.",
            "Names several colors and some letters/numbers.",
            "Knows about everyday things like money and food.",
        ],
        "gross_motor": [
            "Hops on one foot and may skip.",
            "Does a somersault or swings and climbs with confidence.",
        ],
        "fine_motor": [
            "Draws a person with at least 6 body parts.",
            "Prints some letters and numbers.",
            "Uses a fork and spoon well.",
        ],
    },
}


def category_for(domain_key: str) -> str:
    """Return the storage category string for a domain, e.g.
    'child_development:social_emotional'."""
    return f"{CD_CATEGORY_PREFIX}:{domain_key}"


def is_cd_category(category: str | None) -> bool:
    """True for any Child Development category (objectives or private)."""
    if not category:
        return False
    return category == CD_PRIVATE_CATEGORY or category.startswith(CD_CATEGORY_PREFIX + ":")
