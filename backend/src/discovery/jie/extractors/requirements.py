import re
from typing import List, Dict, Any, Tuple
from src.discovery.jie.models import Requirement

# Two separate header vocabularies so a JD's "Nice to have" bullets don't get
# counted as REQUIRED just because they live in the same document as a real
# "Requirements" section. Order matters for the combined regex below (longer/
# more specific phrases first) since re.finditer takes the first alternative
# that matches at each position.
_REQUIRED_HEADERS = [
    r"minimum\s+qualifications", r"basic\s+qualifications", r"required\s+qualifications",
    r"requirements", r"qualifications", r"what\s+you\s+bring", r"must\s+have",
    r"basic\s+skills",
]
_PREFERRED_HEADERS = [
    r"preferred\s+qualifications", r"preferred\s+skills", r"nice\s+to\s+have",
    r"bonus\s+points", r"good\s+to\s+have", r"pluses", r"preferred",
]

_ALL_HEADERS_ALT = "|".join(_REQUIRED_HEADERS + _PREFERRED_HEADERS)

_SECTION_PATTERN = re.compile(
    r"(?P<header>" + _ALL_HEADERS_ALT + r")\s*:\s*"
    # A section body ends at a blank line, a generic capitalized header line,
    # OR the start of another header we actually recognize -- that third
    # branch matters because the first two miss a lowercase header glued
    # directly to the previous section with no blank line ("nice to have:"
    # right after a "Requirements:" bullet list, no capital letter, no blank
    # line between them). Without it, the whole regex is case-insensitive
    # everywhere else but the body-boundary check silently wasn't, so a
    # lowercase "nice to have:" got consumed as more REQUIRED bullets
    # instead of ending the Requirements section.
    r"(?P<body>.*?)(?=\n\s*\n|\n[A-Z][A-Za-z /]{2,40}:|\n\s*(?:" + _ALL_HEADERS_ALT + r")\s*:|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_PREFERRED_HEADER_SET = {h.replace(r"\s+", " ") for h in _PREFERRED_HEADERS}


def _bullets_from_section(section_text: str) -> List[str]:
    bullets = []
    for line in section_text.split("\n"):
        line_clean = line.strip()
        # Bullet markers themselves are [\s\-\*•\d\.\)]+, so a leading digit
        # is ambiguous between "marker" (numbered list: "1. Foo") and
        # "content" ("3+ years of experience..."). Requiring [A-Z] after the
        # marker strip silently dropped every bullet that starts with a
        # number in prose form -- extremely common ("3+ years...", "5 years
        # of..."), so digits are allowed here too.
        if re.match(r"^[\s\-\*•\d\.\)]+\s*([A-Z0-9].*)", line_clean):
            # Two stages so a leading digit that's actually content ("3+
            # years...") isn't eaten as if it were a numbered-list marker
            # ("1. Foo", "2) Bar") -- only a digit run immediately followed
            # by "." or ")" counts as a marker.
            bullet_text = re.sub(r"^[\s\-\*•]+", "", line_clean)
            bullet_text = re.sub(r"^\d+[\.\)]\s*", "", bullet_text).strip()
            if len(bullet_text) > 10 and bullet_text not in bullets:
                bullets.append(bullet_text)
    if not bullets:
        for s in re.split(r"\.\s+", section_text):
            s_clean = s.strip()
            if len(s_clean) > 15:
                bullets.append(s_clean)
    return bullets


def extract_requirements(text: str) -> List[Tuple[str, str]]:
    """
    Extracts requirement bullets from the JD, tagged REQUIRED or PREFERRED
    based on which section header they were found under (e.g. "Nice to
    have:" bullets are PREFERRED, "Requirements:"/"Qualifications:" bullets
    are REQUIRED). Returns a flat list of (bullet_text, importance) so a JD
    with both a required and a preferred section keeps that distinction
    instead of collapsing everything into one undifferentiated block.

    Falls back to sentence-splitting the whole text as REQUIRED-importance
    if no recognizable section header is found at all.
    """
    results: List[Tuple[str, str]] = []
    seen = set()
    any_section = False

    for m in _SECTION_PATTERN.finditer(text):
        any_section = True
        header = m.group("header").strip().lower()
        header_normalized = re.sub(r"\s+", " ", header)
        importance = "PREFERRED" if header_normalized in _PREFERRED_HEADER_SET else "REQUIRED"
        for bullet in _bullets_from_section(m.group("body")):
            if bullet not in seen:
                seen.add(bullet)
                results.append((bullet, importance))

    if not any_section:
        for s in re.split(r"\.\s+", text):
            s_clean = s.strip()
            if len(s_clean) > 15 and s_clean not in seen:
                seen.add(s_clean)
                results.append((s_clean, "REQUIRED"))

    return results


def generate_legacy_requirements(
    requirements_list: List[Tuple[str, str]], tech_list: List[str], skills_list: List[str]
) -> List[Requirement]:
    """Generates Requirement objects from dictionary-matched tech/skills AND
    from the raw requirement bullets extracted above.

    Previously this only used tech_list/skills_list -- a JD's actual
    "Requirements"/"Nice to have" bullets were extracted (see above) but then
    silently discarded, so any JD whose required tools/skills weren't in the
    small skills.json/technologies.json dictionaries produced zero
    Requirement objects even though the JD plainly listed real requirements
    in prose. That starved trust_fit_score (in intent_filter.py) of signal
    it should have had.
    """
    legacy = []
    matched_names_lower = {t.lower() for t in tech_list} | {s.lower() for s in skills_list}

    for tech in tech_list:
        legacy.append(Requirement(
            type="skill",
            name=tech,
            importance="REQUIRED",
            confidence=0.95,
            evidence="Extracted from technologies list.",
        ))

    for skill in skills_list:
        legacy.append(Requirement(
            type="skill",
            name=skill,
            importance="REQUIRED",
            confidence=0.95,
            evidence="Extracted from skills list.",
        ))

    for bullet_text, importance in requirements_list:
        # Skip bullets that are just a restatement of a tech/skill we
        # already captured above with higher confidence -- avoids double-
        # counting "Python" (dictionary hit) and "3+ years of Python" (the
        # bullet it came from) as two separate requirements.
        bullet_lower = bullet_text.lower()
        if any(name in bullet_lower for name in matched_names_lower if len(name) > 2):
            continue
        legacy.append(Requirement(
            type="requirement",
            name=bullet_text[:120],
            importance=importance,
            confidence=0.6,
            evidence=bullet_text,
        ))

    return legacy
