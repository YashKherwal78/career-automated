"""
Tests for Phase 2.2 — Candidate Screening & Comparison

Tests:
  - CandidateAnalyzer (derived CandidateContext, immutability)
  - EligibilityChecker (binary legal constraints, UNKNOWN missing fields)
  - PreferenceMatcher (soft candidate preferences, tri-state evaluation)
  - ScreeningOrchestrator (overall PASS/REJECT determinism, MissingField entries)
  - ComparisonEngine (deterministic scoring, delegates, ComparisonSnapshot)
  - CareerComparisonEngine (backward compatibility shim)
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.career_intelligence.models import (
    CandidateProfile as LegacyCandidateProfile,
    CandidateExperience,
    CandidateSkills,
    PersonalInfo,
)
from src.career_intelligence.candidate_intelligence.models import CandidateContext
from src.career_intelligence.candidate_intelligence.analyzer import CandidateAnalyzer

from src.career_intelligence.job_intelligence.assembler import JobAssembler
from src.career_intelligence.evaluation.resolver import EvaluationContextResolver

from src.career_intelligence.screening.models import (
    MissingField,
    RuleDecision,
    ScreeningResult,
)
from src.career_intelligence.screening.eligibility import EligibilityChecker
from src.career_intelligence.screening.preferences import PreferenceMatcher
from src.career_intelligence.screening.orchestrator import ScreeningOrchestrator

from src.career_intelligence.comparison.engine import ComparisonEngine, CareerComparisonEngine


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

class SampleCandidateWrapper:
    """Test candidate wrapper providing attributes for CandidateProfile, preferences, and eligibility."""
    def __init__(self, profile, **kwargs):
        self.profile = profile
        self.experience = profile.experience
        self.skills = profile.skills
        self.personal_info = profile.personal_info
        self.years_experience = kwargs.get("years_experience", 6.0)
        self.remote_allowed = kwargs.get("remote_allowed", True)
        self.minimum_salary = kwargs.get("minimum_salary", 130000.0)
        self.citizenship = kwargs.get("citizenship", "US")
        self.visa_status = kwargs.get("visa_status", "Citizen")
        self.clearance = kwargs.get("clearance", "None")
        self.preferred_locations = kwargs.get("preferred_locations", ["San Francisco, CA", "Remote"])
        self.requires_sponsorship = kwargs.get("requires_sponsorship", False)


def create_sample_candidate(**kwargs):
    """Create a structured CandidateProfile instance wrapped for screening testing."""
    profile = LegacyCandidateProfile(
        summary="Senior Backend Engineer with 6 years experience in Python and PostgreSQL.",
        experience=[
            CandidateExperience(
                company="TechCorp",
                role="Senior Backend Engineer",
                start_date="2020-01",
                end_date="Present",
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
            ),
            CandidateExperience(
                company="DataInc",
                role="Software Engineer",
                start_date="2018-01",
                end_date="2020-01",
                technologies=["Python", "Django", "MySQL"],
            ),
        ],
        skills=CandidateSkills(
            programming_languages=["Python", "Go", "SQL"],
            frameworks=["FastAPI", "Django"],
            databases=["PostgreSQL", "Redis"],
            cloud=["AWS", "Docker"],
        ),
        personal_info=PersonalInfo(
            full_name="Alex Mercer",
            location="San Francisco, CA, US",
        ),
    )
    return SampleCandidateWrapper(profile, **kwargs)


def create_sample_eval_context():
    """Create a canonical EvaluationContext using JobAssembler & Resolver."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    jd = """
    Senior Backend Engineer needed for platform team.
    Requirements:
    - 5+ years backend development experience
    - Proficiency in Python, PostgreSQL, Redis, Docker
    - Location: San Francisco, CA or Remote
    - Must be a US Citizen (security requirement)
    - Salary: $140,000 - $180,000
    - Visa sponsorship unavailable.
    """
    structured = assembler.process(title="Senior Backend Engineer", jd_text=jd)
    ctx = resolver.resolve(structured)
    return ctx.model_copy(update={"metadata": {"citizenship_required": "US"}})


# ---------------------------------------------------------------------------
# CandidateAnalyzer Tests
# ---------------------------------------------------------------------------

def test_candidate_analyzer_derives_facts():
    """CandidateAnalyzer must derive CandidateContext facts without job knowledge."""
    profile = create_sample_candidate()
    analyzer = CandidateAnalyzer()
    cand_ctx = analyzer.analyze(profile)

    assert isinstance(cand_ctx, CandidateContext)
    assert cand_ctx.inferred_level.value == "senior"
    assert cand_ctx.years_experience >= 6.0
    domain_names = [d.value for d in cand_ctx.primary_domains]
    assert "backend" in domain_names
    assert len(cand_ctx.capability_vector) > 0


def test_candidate_context_immutable():
    """CandidateContext must be frozen/immutable."""
    profile = create_sample_candidate()
    analyzer = CandidateAnalyzer()
    cand_ctx = analyzer.analyze(profile)
    try:
        cand_ctx.years_experience = 10.0
        assert False, "CandidateContext should be immutable"
    except (TypeError, ValueError, AttributeError):
        pass  # Expected


# ---------------------------------------------------------------------------
# Screening Layer Tests (Eligibility & Preferences)
# ---------------------------------------------------------------------------

def test_eligibility_checker_pass():
    """EligibilityChecker should PASS when legal facts satisfy context."""
    checker = EligibilityChecker()
    eval_ctx = create_sample_eval_context()
    cand = create_sample_candidate()

    res = checker.check_all(eval_ctx, cand)
    decisions = [r.decision for r in res]
    assert RuleDecision.REJECT not in decisions


def test_eligibility_checker_reject_citizenship():
    """EligibilityChecker should REJECT when citizenship mismatches requirement."""
    checker = EligibilityChecker()
    eval_ctx = create_sample_eval_context()

    # Create candidate requiring foreign citizenship
    cand = create_sample_candidate(citizenship="Canada")

    res = checker.check_citizenship(eval_ctx, cand)
    assert res.decision == RuleDecision.REJECT


def test_eligibility_checker_unknown_missing_field():
    """Missing legal attributes should produce UNKNOWN decision."""
    checker = EligibilityChecker()
    eval_ctx = create_sample_eval_context()

    # Candidate with None citizenship
    cand = create_sample_candidate(citizenship=None)

    res = checker.check_citizenship(eval_ctx, cand)
    assert res.decision == RuleDecision.UNKNOWN
    assert res.field == "citizenship"


def test_preference_matcher_pass():
    """PreferenceMatcher should PASS matching work mode and salary."""
    matcher = PreferenceMatcher()
    eval_ctx = create_sample_eval_context()
    cand = create_sample_candidate()

    results = matcher.match_all(eval_ctx, cand)
    decisions = [r.decision for r in results]
    assert RuleDecision.REJECT not in decisions


def test_preference_matcher_reject_work_mode():
    """PreferenceMatcher should REJECT when work mode conflicts with negative preference."""
    matcher = PreferenceMatcher()
    eval_ctx = create_sample_eval_context()
    cand = create_sample_candidate(remote_allowed=False)

    # Set job to Remote, candidate remote_allowed = False
    eval_ctx_remote = eval_ctx.model_copy(update={"work_mode": "Remote"})

    res = matcher.match_work_mode(eval_ctx_remote, cand)
    assert res.decision == RuleDecision.REJECT


def test_screening_orchestrator_deterministic_pass():
    """Orchestrator must return overall PASS when no conflicts exist."""
    orchestrator = ScreeningOrchestrator()
    eval_ctx = create_sample_eval_context()
    cand = create_sample_candidate()

    result = orchestrator.screen(eval_ctx, cand)
    assert isinstance(result, ScreeningResult)
    assert result.overall == "PASS"
    assert len(result.conflicts) == 0


def test_screening_orchestrator_deterministic_reject():
    """Orchestrator must return overall REJECT when a conflict exists."""
    orchestrator = ScreeningOrchestrator()
    eval_ctx = create_sample_eval_context()

    # Force visa conflict
    eval_ctx_no_sponsor = eval_ctx.model_copy(update={"visa_sponsorship": "No"})
    cand = create_sample_candidate(visa_status="Requires Sponsorship", requires_sponsorship=True)

    result = orchestrator.screen(eval_ctx_no_sponsor, cand)
    assert result.overall == "REJECT"
    assert len(result.conflicts) > 0


def test_screening_unknown_does_not_reject():
    """Missing fields produce MissingField items in 'unknown' list, but do NOT trigger REJECT."""
    orchestrator = ScreeningOrchestrator()
    eval_ctx = create_sample_eval_context()
    cand = create_sample_candidate(remote_allowed=None, preferred_locations=None, minimum_salary=None)

    result = orchestrator.screen(eval_ctx, cand)
    assert result.overall == "PASS"
    assert len(result.unknown) > 0
    missing_fields = [m.field for m in result.unknown]
    assert "work_mode" in missing_fields or "preferred_locations" in missing_fields


# ---------------------------------------------------------------------------
# ComparisonEngine Tests
# ---------------------------------------------------------------------------

def test_comparison_engine_deterministic_score():
    """ComparisonEngine output must be identical for identical inputs."""
    engine = ComparisonEngine()
    eval_ctx = create_sample_eval_context()
    analyzer = CandidateAnalyzer()
    cand = create_sample_candidate()
    cand_ctx = analyzer.analyze(cand)

    res1 = engine.compare(eval_ctx, cand_ctx, candidate_profile=cand)
    res2 = engine.compare(eval_ctx, cand_ctx, candidate_profile=cand)

    assert res1["overall_score"] == res2["overall_score"]
    assert res1["snapshot"].hash_value == res2["snapshot"].hash_value


def test_comparison_engine_scoring_breakdown():
    """ComparisonEngine must calculate dimensional scores and generate reproducible snapshot."""
    engine = ComparisonEngine()
    eval_ctx = create_sample_eval_context()
    analyzer = CandidateAnalyzer()
    cand = create_sample_candidate()
    cand_ctx = analyzer.analyze(cand)

    res = engine.compare(eval_ctx, cand_ctx, candidate_profile=cand)

    assert res["overall_score"] > 0.0
    assert "skills" in res["breakdown"]
    assert "technologies" in res["breakdown"]
    assert "experience" in res["breakdown"]
    assert res["snapshot"].snapshot_id.startswith("snap_")


def test_comparison_engine_rejected_job_zeroes_score():
    """A rejected screening result must yield overall_score = 0.0."""
    engine = ComparisonEngine()
    eval_ctx = create_sample_eval_context()
    eval_ctx_no_visa = eval_ctx.model_copy(update={"visa_sponsorship": "No"})

    analyzer = CandidateAnalyzer()
    cand = create_sample_candidate(visa_status="Requires Sponsorship", requires_sponsorship=True)
    cand_ctx = analyzer.analyze(cand)

    res = engine.compare(eval_ctx_no_visa, cand_ctx, candidate_profile=cand)
    assert res["screening"].overall == "REJECT"
    assert res["overall_score"] == 0.0


def test_legacy_career_comparison_engine_shim():
    """CareerComparisonEngine backward compatibility shim must pass legacy calls."""
    shim = CareerComparisonEngine()
    cand = create_sample_candidate()

    assembler = JobAssembler()
    structured_job = assembler.process(
        title="Senior Backend Engineer",
        jd_text="5+ years Python experience required.",
    )

    comp_res = shim.compare(cand, structured_job)
    assert comp_res.profile_version == "2.0.0"
    assert comp_res.skills.score >= 0.0
    assert comp_res.experience.required_years == 5


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all Phase 2.2 tests."""
    tests = [
        # CandidateAnalyzer
        test_candidate_analyzer_derives_facts,
        test_candidate_context_immutable,
        # Eligibility & Preferences
        test_eligibility_checker_pass,
        test_eligibility_checker_reject_citizenship,
        test_eligibility_checker_unknown_missing_field,
        test_preference_matcher_pass,
        test_preference_matcher_reject_work_mode,
        test_screening_orchestrator_deterministic_pass,
        test_screening_orchestrator_deterministic_reject,
        test_screening_unknown_does_not_reject,
        # ComparisonEngine
        test_comparison_engine_deterministic_score,
        test_comparison_engine_scoring_breakdown,
        test_comparison_engine_rejected_job_zeroes_score,
        test_legacy_career_comparison_engine_shim,
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
    print(f"Phase 2.2 Tests: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All Phase 2.2 tests passed!")


if __name__ == "__main__":
    run_all_tests()
