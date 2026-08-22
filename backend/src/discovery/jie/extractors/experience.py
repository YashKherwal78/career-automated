import re
from typing import Optional, List, Tuple
from src.discovery.jie.extractors.base import BaseExtractor
from src.discovery.jie.models import ExperienceInfo

# Compile regex patterns once at module level
RANGE_PATTERN = re.compile(
    r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s*(?:-|to|–)\s*(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\+?\s*(?:years?|yrs?|Yrs)',
    re.IGNORECASE
)
PLUS_PATTERN = re.compile(
    r'\b(?:minimum|at\s+least|have)?\s*(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\+?\s*(?:or\s+more\s+)?(?:years?|yrs?|Yrs)',
    re.IGNORECASE
)
ENTRY_LEVEL_PATTERN = re.compile(
    r'\b(fresh graduate|fresher|0\s*(?:-|to|–)\s*1?\s*(?:years?|yrs?)|entry level|early career|recent graduates?|no experience required|graduate program)\b',
    re.IGNORECASE
)

# A years-of-experience number immediately preceded by one of these is a
# nested sub-clause describing a specialization WITHIN the primary
# requirement (e.g. "5+ years of experience..., including at least 1 year
# focused on Generative AI") -- not the primary requirement itself.
SUBCLAUSE_PRECEDING_PATTERN = re.compile(
    r'(?:including|of\s+which|particularly|specifically|plus(?:\s+an?)?\s+additional)\s*$',
    re.IGNORECASE
)
# A years-of-experience number near one of these is an optional/nice-to-have
# tier, not a hard minimum requirement (e.g. "5+ years preferred").
OPTIONAL_NEARBY_PATTERN = re.compile(
    r'\b(?:preferred|nice[\s-]to[\s-]have|a\s+plus|bonus|ideally)\b',
    re.IGNORECASE
)

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

class ExperienceExtractor(BaseExtractor):
    def __init__(self):
        pass

    def parse_number(self, val: str) -> int:
        """Parses a digit string or text word representation of a number."""
        val_clean = val.strip().lower()
        if val_clean.isdigit():
            return int(val_clean)
        return WORD_NUMBERS.get(val_clean, 0)

    def _is_subordinate_or_optional(self, text: str, match: "re.Match[str]") -> bool:
        """True if this match is a nested sub-clause (a specialization within
        the primary requirement) or an optional/preferred tier -- either way,
        not the primary years-of-experience requirement. Checked via a small
        window of surrounding text rather than the whole JD, since these
        marker phrases apply locally to the clause containing the number."""
        preceding = text[max(0, match.start() - 40):match.start()]
        if SUBCLAUSE_PRECEDING_PATTERN.search(preceding):
            return True
        following = text[match.end():match.end() + 40]
        if OPTIONAL_NEARBY_PATTERN.search(preceding) or OPTIONAL_NEARBY_PATTERN.search(following):
            return True
        return False

    def find_range(self, text: str) -> List[Tuple[int, int]]:
        """Finds experience range patterns (e.g. 3-5 years) in text."""
        matches = []
        for m in RANGE_PATTERN.finditer(text):
            if self._is_subordinate_or_optional(text, m):
                continue
            try:
                min_val = self.parse_number(m.group(1))
                max_val = self.parse_number(m.group(2))
                matches.append((min_val, max_val))
            except Exception:
                pass
        return matches

    def find_plus(self, text: str) -> List[int]:
        """Finds experience bound patterns (e.g. 3+ years) in text."""
        matches = []
        for m in PLUS_PATTERN.finditer(text):
            if self._is_subordinate_or_optional(text, m):
                continue
            try:
                val = self.parse_number(m.group(1))
                matches.append(val)
            except Exception:
                pass
        return matches

    def find_entry_level(self, text: str) -> bool:
        """Determines if the text contains entry-level/fresher signals."""
        return bool(ENTRY_LEVEL_PATTERN.search(text))

    def normalize(self, ranges: List[Tuple[int, int]], bounds: List[int], entry_level: bool) -> ExperienceInfo:
        """Resolves raw extraction conflicts and returns canonical ExperienceInfo model."""
        info = ExperienceInfo(experience_min=None, experience_max=None, fresher_friendly=False)
        
        # 1. Evaluate entry level/fresher status
        if entry_level:
            info.fresher_friendly = True
            info.experience_min = 0
            
        # 2. Pick range matches if present (usually most specific)
        if ranges:
            # Sort by min experience to resolve conflicts: pick the most common or lowest non-zero requirement
            ranges.sort(key=lambda x: x[0])
            info.experience_min = ranges[0][0]
            info.experience_max = ranges[0][1]
        # 3. Fall back to bounds matches (e.g. "3+ years")
        elif bounds:
            bounds.sort()
            info.experience_min = bounds[0]
            
        # Guarantee fresher_friendly aligns with min experience of 0 or 1
        if info.experience_min is not None:
            if info.experience_min <= 1:
                info.fresher_friendly = True
            else:
                info.fresher_friendly = False
            
        return info

    def extract(self, text: str, **kwargs) -> ExperienceInfo:
        """Extracts experience requirements by scanning and resolving conflicts from text."""
        ranges = self.find_range(text)
        bounds = self.find_plus(text)
        entry_level = self.find_entry_level(text)
        return self.normalize(ranges, bounds, entry_level)
