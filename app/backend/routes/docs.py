"""Serve filtered pillar guide content from docs/ markdown files."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, require_admin
from models import User

router = APIRouter(prefix="/api/docs", tags=["docs"])

DOCS_DIR = Path(__file__).parent.parent.parent.parent / "docs"
GUIDES_DIR = DOCS_DIR / "pillar_guides"

# Map pillar keys to their doc file(s)
PILLAR_DOCS = {
    "spiritual": ["07_spiritual_warfare_discernment.md"],
    "financial": ["15_financial_development_investment_literacy.md"],
    "education": ["01_career_guidance_template.md"],
    "character": ["02_consequence_analysis.md"],
    "life_skills": ["16_life_skills_practical_competence.md"],
    "heritage": ["05_heritage_identity.md"],
    "economy": ["03_family_economy_system.md", "04_bounty_framework.md"],
    "resilience": ["06_environmental_resilience.md"],
    "dimensional_navigation": ["09_dimensional_navigation.md"],
    "civic": ["10_civic_institutional_navigation.md"],
    "scientific_reality_testing": ["11_scientific_method_reality_testing.md", "11a_lost_knowledge_corruption_institutional_blindness.md"],
    "inheritance_burden_stewardship": ["12_inheritance_burden_stewardship.md"],
    "catholic_formation": ["13_catholic_sacramental_formation_domestic_church.md", "14a_recidivism_forgiveness_forgetting_addendum.md"],
    "secular_sacred_formation": ["14_secular_sacred_formation_civilizational_literacy.md", "14a_recidivism_forgiveness_forgetting_addendum.md"],
}

# Section headings that should be excluded (age bands, implementation details)
EXCLUDE_SECTIONS = re.compile(
    r"^#+\s*(Age-Band Milestones|Ages?\s+\d|Application Concepts|Application Features|"
    r"Desired Application Features|Visual Board Concepts|Record Types|"
    r"Catholic Formation Records|Catholic Formation Dashboard|"
    r"Desired Outcome|Implementation|Minimal UI|Suggested Data|"
    r"First Implementation|New Pillar Definitions|Addenda Attachments|"
    r"Recommended File Placement|Recommended New Pillars|Recommended Addenda|"
    r"Suggested Shared Age Bands|Recommendation$)",
    re.IGNORECASE,
)


def filter_markdown(content: str) -> str:
    """Remove age-band milestone sections and implementation details, keep philosophy."""
    lines = content.split("\n")
    result = []
    skip_level = None  # heading level we're skipping (and all deeper)
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip code blocks that are just internal identifiers (```text\nsome_key\n```)
        if line.strip().startswith("```"):
            block_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            block_text = "\n".join(block_lines).strip()
            # Keep it only if it's a meaningful multi-line diagram or explanation
            if "\n" in block_text or len(block_text) > 40:
                if skip_level is None:
                    result.append("```")
                    result.extend(block_lines)
                    result.append("```")
            continue

        heading_match = re.match(r"^(#+)\s+", line)
        if heading_match:
            level = len(heading_match.group(1))
            if skip_level is not None:
                if level <= skip_level:
                    skip_level = None  # we've exited the excluded section
                else:
                    i += 1
                    continue  # still inside excluded section
            if EXCLUDE_SECTIONS.match(line):
                skip_level = level
                i += 1
                continue
        elif skip_level is not None:
            i += 1
            continue

        result.append(line)
        i += 1

    # Clean up excessive blank lines
    text = "\n".join(result)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@router.get("/{pillar}")
def get_pillar_guide(pillar: str, _: User = Depends(require_admin)):
    """Return filtered markdown guide content for a pillar (admin only).

    Checks for a dedicated pillar guide in docs/pillar_guides/ first.
    Falls back to filtered raw doc content if no dedicated guide exists.
    """
    # Check for a dedicated pillar guide first
    guide_path = GUIDES_DIR / f"{pillar}.md"
    if guide_path.exists():
        content = guide_path.read_text(encoding="utf-8").strip()
        return {"pillar": pillar, "content": content}

    # Fall back to filtered raw doc files
    doc_files = PILLAR_DOCS.get(pillar)
    if doc_files is None:
        raise HTTPException(status_code=404, detail="Unknown pillar")
    if not doc_files:
        return {"pillar": pillar, "content": ""}

    sections = []
    seen_files = set()
    for filename in doc_files:
        if filename in seen_files:
            continue
        seen_files.add(filename)
        filepath = DOCS_DIR / filename
        if filepath.exists():
            raw = filepath.read_text(encoding="utf-8")
            sections.append(filter_markdown(raw))

    return {"pillar": pillar, "content": "\n\n---\n\n".join(sections)}
