"""
Test suite for TypographyLayoutEngine module.
Verifies font scale ladder, line stretch scaling, locked margins, and optical balance rules.
"""

import pytest
from src.resume_intelligence.tailoring.typography_layout_engine import TypographyLayoutEngine, LayoutMetrics


def test_typography_engine_hard_limits():
    engine = TypographyLayoutEngine()
    assert engine.TARGET_UTIL_MIN == 92.0
    assert engine.TARGET_UTIL_MAX == 96.0
    assert engine.HARD_UTIL_MAX == 98.0


def test_optical_balance_check():
    engine = TypographyLayoutEngine()
    good_metrics = LayoutMetrics(
        page_count=1,
        page_utilization=94.5,
        font_size_pt=11.0,
        line_stretch=1.04,
        section_proportions={
            "Experience": 0.52,
            "Projects": 0.16,
            "Education": 0.10,
            "Technical Skills": 0.11
        }
    )
    assert engine._check_optical_balance(good_metrics) is True


def test_optical_balance_fails_if_overflow():
    engine = TypographyLayoutEngine()
    overflow_metrics = LayoutMetrics(
        page_count=1,
        page_utilization=99.2,
        font_size_pt=11.0
    )
    assert engine._check_optical_balance(overflow_metrics) is False
