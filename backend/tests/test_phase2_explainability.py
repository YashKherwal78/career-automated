"""
Tests for Phase 2.3 — Explainability & Recruiter Intelligence

Tests:
  - EvidenceBuilder (strengths, weaknesses, missing capabilities, screening observations)
  - RecruiterIntelligence (recommendations, executive summary, interview questions)
  - Invariant Test: Explainability layer never modifies numerical scores.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.join(os.path.dirname(__file__), ".."))))

from src.career_intelligence.explainability.models import (
    EvidenceReport,
    RecruiterSummary,
)
from src.career_intelligence.explainability.evidence_builder import EvidenceBuilder
from src.career_intelligence.explainability.recruiter_intelligence import RecruiterIntelligence
from src.career_intelligence.screening.models import ScreeningResult, MissingField


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

def create_dummy_comparison_result(overall_score=85.0, screening_overall="PASS"):
    """Create mock ComparisonEngine.compare() output dict."""
    screening = ScreeningResult(
        overall=screening_overall,
        matched=["work_mode_preference", "citizenship_eligibility"],
        conflicts=["[visa_sponsorship] No visa sponsorship offered"] if screening_overall == "REJECT" else [],
        unknown=[MissingField(field="salary", reason="Minimum salary missing")],
    )

    return {
        "comparison_id": "cmp_test123",
        "overall_score": overall_score if screening_overall == "PASS" else 0.0,
        "screening": screening,
        "breakdown": {"skills": 90.0, "technologies": 80.0, "experience": 85.0, "domain": 85.0},
        "matched_skills": ["Python", "REST API", "System Design"],
        "missing_skills": ["GraphQL"],
        "matched_techs": ["FastAPI", "PostgreSQL", "Docker"],
        "missing_techs": ["Kubernetes", "Redis"],
        "matched_domains": ["backend"],
        "experience_gap_years": 0.0,
        "snapshot": None,
    }


# ---------------------------------------------------------------------------
# EvidenceBuilder Tests
# ---------------------------------------------------------------------------

def test_evidence_builder_report():
    """EvidenceBuilder should generate structured EvidenceReport without recomputing scores."""
    builder = EvidenceBuilder()
    res = create_dummy_comparison_result(overall_score=85.0)

    report = builder.build_report(res)
    assert isinstance(report, EvidenceReport)
    assert report.overall_score == 85.0
    assert len(report.strengths) > 0
    assert len(report.missing_capabilities) > 0
    assert len(report.positive_semantic_matches) > 0
    assert len(report.screening_observations) > 0


def test_evidence_builder_never_modifies_score():
    """EvidenceBuilder must faithfully reflect score without altering it."""
    builder = EvidenceBuilder()
    res = create_dummy_comparison_result(overall_score=72.5)

    report = builder.build_report(res)
    assert report.overall_score == 72.5
    assert res["overall_score"] == 72.5  # Input dict untouched


# ---------------------------------------------------------------------------
# RecruiterIntelligence Tests
# ---------------------------------------------------------------------------

def test_recruiter_intelligence_strong_hire():
    """High score + PASS screening must yield STRONG_HIRE recommendation."""
    intel = RecruiterIntelligence()
    res = create_dummy_comparison_result(overall_score=88.0, screening_overall="PASS")

    summary = intel.generate_summary(res, job_title="Senior Backend Engineer")
    assert isinstance(summary, RecruiterSummary)
    assert summary.overall_recommendation == "STRONG_HIRE"
    assert summary.overall_score == 88.0
    assert len(summary.top_strengths) > 0
    assert len(summary.interview_focus_areas) > 0


def test_recruiter_intelligence_do_not_advance_on_reject():
    """REJECT screening status must yield DO_NOT_ADVANCE recommendation."""
    intel = RecruiterIntelligence()
    res = create_dummy_comparison_result(overall_score=85.0, screening_overall="REJECT")

    summary = intel.generate_summary(res, job_title="Senior Backend Engineer")
    assert summary.overall_recommendation == "DO_NOT_ADVANCE"
    assert summary.overall_score == 0.0


def test_recruiter_intelligence_interview_questions():
    """RecruiterIntelligence must generate targeted interview questions for missing capabilities."""
    intel = RecruiterIntelligence()
    res = create_dummy_comparison_result(overall_score=75.0)

    summary = intel.generate_summary(res, job_title="Backend Engineer")
    topics = [q.topic for q in summary.interview_focus_areas]
    assert "Kubernetes" in topics or "Redis" in topics or "GraphQL" in topics


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all Phase 2.3 tests."""
    tests = [
        test_evidence_builder_report,
        test_evidence_builder_never_modifies_score,
        test_recruiter_intelligence_strong_hire,
        test_recruiter_intelligence_do_not_advance_on_reject,
        test_recruiter_intelligence_interview_questions,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  ✅ {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Phase 2.3 Tests: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All Phase 2.3 tests passed!")


if __name__ == "__main__":
    run_all_tests()
