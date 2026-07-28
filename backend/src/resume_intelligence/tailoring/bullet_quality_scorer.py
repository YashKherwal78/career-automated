"""
Deterministic Bullet Quality Scorer & Rewrite Level Router.

Scoring Rubric (100 Points Total):
- Action Verb Strength: 20 pts
- Metric Presence: 15 pts
- Google XYZ Structure (Accomplished [X] by [Y] as measured by [Z]): 20 pts
- Readability / Flesch Score proxy: 15 pts
- PM Keyword Relevance: 15 pts
- Grammar & Punctuation: 10 pts
- Word Count Sanity (18-28 words): 5 pts

Rewrite Levels:
- Score >= 95: KEEP (No action)
- Score 90-94: MICRO_EDIT (Verb swap only)
- Score 80-89: LIGHT_REWRITE (Minor polish, preserve structure)
- Score 70-79: MODERATE_REWRITE (Sentence restructure, preserve facts)
- Score < 70:  FULL_REWRITE (Surgical overhaul)
"""

import re
import logging
from enum import Enum
from typing import List, Set, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RewriteLevel(str, Enum):
    KEEP = "KEEP"
    MICRO_EDIT = "MICRO_EDIT"
    LIGHT_REWRITE = "LIGHT_REWRITE"
    MODERATE_REWRITE = "MODERATE_REWRITE"
    FULL_REWRITE = "FULL_REWRITE"


class BulletScoreResult(BaseModel):
    bullet_text: str
    total_score: int
    verb_score: int
    metric_score: int
    xyz_score: int
    readability_score: int
    pm_keyword_score: int
    grammar_score: int
    length_score: int
    rewrite_level: RewriteLevel
    jd_relevance: float = 0.5  # 0.0 to 1.0


class DeterministicBulletScorer:
    """
    Evaluates a single resume bullet deterministically against a 100-point rubric.
    """

    STRONG_VERBS: Set[str] = {
        "led", "delivered", "launched", "drove", "architected", "productized",
        "defined", "scaled", "spearheaded", "scoped", "shipped", "orchestrated",
        "pioneered", "built", "optimized", "increased", "decreased", "reduced"
    }

    PM_KEYWORDS: Set[str] = {
        "customer discovery", "user research", "prd", "rice", "roadmap",
        "mvp", "funnel", "conversion", "a/b testing", "gtm", "dau", "mau",
        "gmv", "cross-functional", "sprint", "prioritization", "scrum"
    }

    # Adaptive thresholds per section
    SECTION_THRESHOLDS = {
        "Summary": 75,
        "Experience": 85,
        "Projects": 82,
        "Skills": 100,
    }

    def score(self, bullet_text: str, section_name: str = "Experience", jd_keywords: List[str] = None) -> BulletScoreResult:
        bullet_lower = bullet_text.lower().strip()
        words = bullet_lower.split()
        word_count = len(words)

        # 1. Action Verb (20 pts)
        first_word = words[0] if words else ""
        if first_word in self.STRONG_VERBS:
            verb_score = 20
        elif re.match(r"^[a-z]+ed\b", first_word):
            verb_score = 15
        else:
            verb_score = 5

        # 2. Metric Present (15 pts)
        has_number = bool(re.search(r"\b\d+(?:\.\d+)?%?|\$\d+|\b\d+\+\b", bullet_text))
        metric_score = 15 if has_number else 0

        # 3. Google XYZ Structure (20 pts)
        has_action = verb_score >= 15
        has_method = any(kw in bullet_lower for kw in ["by", "via", "through", "using", "from", "after"])
        has_result = metric_score == 15
        if has_action and has_method and has_result:
            xyz_score = 20
        elif has_action and has_result:
            xyz_score = 15
        else:
            xyz_score = 5

        # 4. Readability (15 pts)
        # Penalize overlong run-on sentences (>32 words) or overly short (<10 words)
        if 15 <= word_count <= 26:
            readability_score = 15
        elif 10 <= word_count <= 30:
            readability_score = 10
        else:
            readability_score = 5

        # 5. PM Keyword Relevance (15 pts)
        pm_matches = sum(1 for kw in self.PM_KEYWORDS if kw in bullet_lower)
        if jd_keywords:
            pm_matches += sum(1 for kw in jd_keywords if kw.lower() in bullet_lower)
        pm_keyword_score = min(15, pm_matches * 5)

        # 6. Grammar & Punctuation (10 pts)
        grammar_score = 10 if bullet_text.strip().endswith((".", "!", "%", "}")) else 5

        # 7. Word Count Sanity (5 pts)
        length_score = 5 if 18 <= word_count <= 24 else 3

        total = verb_score + metric_score + xyz_score + readability_score + pm_keyword_score + grammar_score + length_score

        # Determine Rewrite Level based on total score
        if total >= 95:
            level = RewriteLevel.KEEP
        elif total >= 90:
            level = RewriteLevel.MICRO_EDIT
        elif total >= 80:
            level = RewriteLevel.LIGHT_REWRITE
        elif total >= 70:
            level = RewriteLevel.MODERATE_REWRITE
        else:
            level = RewriteLevel.FULL_REWRITE

        return BulletScoreResult(
            bullet_text=bullet_text,
            total_score=total,
            verb_score=verb_score,
            metric_score=metric_score,
            xyz_score=xyz_score,
            readability_score=readability_score,
            pm_keyword_score=pm_keyword_score,
            grammar_score=grammar_score,
            length_score=length_score,
            rewrite_level=level
        )
