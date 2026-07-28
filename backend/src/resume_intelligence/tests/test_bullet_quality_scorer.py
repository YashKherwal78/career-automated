"""
Test suite for DeterministicBulletScorer.
"""

import pytest
from src.resume_intelligence.tailoring.bullet_quality_scorer import DeterministicBulletScorer, RewriteLevel


def test_perfect_bullet_scores_keep():
    scorer = DeterministicBulletScorer()
    bullet = "Launched Stymo multi-vendor marketplace, driving 123,000 sessions and Rs. 374,000 GMV in 45 days via social GTM."
    res = scorer.score(bullet, section_name="Experience")

    assert res.total_score >= 90
    assert res.rewrite_level in [RewriteLevel.KEEP, RewriteLevel.MICRO_EDIT]
    assert res.metric_score == 15
    assert res.verb_score == 20


def test_weak_bullet_gets_rewrite_level():
    scorer = DeterministicBulletScorer()
    bullet = "worked on some code for backend."
    res = scorer.score(bullet, section_name="Experience")

    assert res.total_score < 70
    assert res.rewrite_level == RewriteLevel.FULL_REWRITE
    assert res.metric_score == 0
