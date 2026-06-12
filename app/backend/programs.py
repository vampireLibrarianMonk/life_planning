"""Program definitions — structured bounty tracks."""

PROGRAMS = [
    {
        "key": "military_prep",
        "title": "Military Preparation",
        "icon": "🎖️",
        "description": "5-phase progression from orientation to decision point. Discipline, knowledge, standards, technical skills.",
        "categories": ["military_prep"],
    },
    {
        "key": "catholic_practices",
        "title": "Catholic Practices",
        "icon": "⛪",
        "description": "Weekly, seasonal, and annual devotional practices. Mass, confession, prayer, service.",
        "categories": ["catholic"],
    },
    {
        "key": "research",
        "title": "Research Bounties",
        "icon": "📚",
        "description": "Saint, paradox, and effect fact sheets. Template design + topic-based research.",
        "categories": ["saint", "paradox", "effect"],
    },
    {
        "key": "marriage_prep",
        "title": "Marriage Preparation",
        "icon": "💍",
        "description": "Pre-Cana (Catholic) and secular marriage preparation pathways. Covenant-level commitment.",
        "categories": ["catholic", "secular_sacred_formation"],
        "filter_titles": ["Pre-Cana", "Marriage Preparation"],
    },
    {
        "key": "fleet_maintenance",
        "title": "Fleet Maintenance (PMCS)",
        "icon": "🚗",
        "description": "Weekly vehicle inspections. Design the template, maintain the streak, earn the car.",
        "categories": ["pmcs"],
    },
]
