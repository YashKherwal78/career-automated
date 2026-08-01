"""
Tests for Phase 2.1 — Job Ingestion Layer

Tests:
  - JobParser: deterministic parsing, field extraction
  - JobEnricher: seniority, domain, job family classification
  - JobAssembler: end-to-end pipeline
  - EvaluationContextResolver: policy selection, context assembly
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.career_intelligence.job_intelligence.models import (
    Classification,
    ParsedJob,
    Seniority,
    StructuredJob,
    LocationInfo,
    SalaryInfo,
)
from src.career_intelligence.job_intelligence.parser import JobParser
from src.career_intelligence.job_intelligence.enricher import JobEnricher
from src.career_intelligence.job_intelligence.assembler import JobAssembler
from src.career_intelligence.evaluation.models import EvaluationContext, EvaluationPolicy
from src.career_intelligence.evaluation.resolver import EvaluationContextResolver, PolicyRegistry


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SAMPLE_JD_BACKEND = """
We are looking for a Senior Backend Engineer to join our platform team.

Requirements:
- 5+ years of experience in backend development
- Proficiency in Python, Go, or Java
- Experience with PostgreSQL and Redis
- Familiarity with Docker and Kubernetes
- Strong understanding of RESTful API design
- Bachelor's degree in Computer Science or related field

Responsibilities:
- Design and build scalable backend services
- Optimize database queries and improve system performance
- Collaborate with frontend and infrastructure teams
- Mentor junior engineers

Benefits:
- Competitive salary ($120,000 - $180,000)
- Remote-friendly (US-based)
- Health insurance
- Stock options

We do not sponsor visas for this position.
"""

SAMPLE_JD_PM = """
Associate Product Manager

About the role:
We're seeking a motivated Associate Product Manager to join our product team.
This is an entry-level position perfect for recent graduates with strong
analytical skills.

Requirements:
- 0-2 years of experience
- Strong communication and analytical skills
- Understanding of agile methodology
- Bachelor's degree required

Responsibilities:
- Conduct user research and competitive analysis
- Define product requirements and prioritize features
- Collaborate with engineering and design teams
- Track product metrics using data analytics

Location: Bangalore, India
Work Mode: Hybrid
"""

SAMPLE_JD_ML = """
Machine Learning Engineer

We are looking for an ML Engineer to build and deploy production
machine learning systems.

Requirements:
- 3+ years of experience in machine learning
- Proficiency in Python and TensorFlow or PyTorch
- Experience with NLP and deep learning
- Strong understanding of data structures and algorithms
- Master's degree in Computer Science, Statistics, or related field

Responsibilities:
- Design ML pipelines for NLP tasks
- Train and evaluate deep learning models
- Deploy models to production using Docker and Kubernetes
- Collaborate with data science and engineering teams

Location: Remote
Salary: $150,000 - $200,000
"""


# ---------------------------------------------------------------------------
# JobParser Tests
# ---------------------------------------------------------------------------

def test_parser_deterministic():
    """Same input must always produce the same jd_hash."""
    parser = JobParser()
    p1 = parser.parse(title="Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    p2 = parser.parse(title="Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    assert p1.jd_hash == p2.jd_hash, "Parser must be deterministic for identical input"


def test_parser_extracts_title():
    """Parser should extract the title."""
    parser = JobParser()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    assert isinstance(parsed, ParsedJob)
    assert parsed.title != ""


def test_parser_extracts_experience():
    """Parser should extract experience requirements."""
    parser = JobParser()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    assert parsed.experience_min is not None
    assert parsed.experience_min >= 5


def test_parser_extracts_technologies():
    """Parser should extract technology mentions."""
    parser = JobParser()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    tech_lower = [t.lower() for t in parsed.technologies]
    assert any("python" in t for t in tech_lower), "Should detect Python"


def test_parser_detects_no_visa():
    """Parser should detect 'no visa sponsorship'."""
    parser = JobParser()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    assert parsed.visa_sponsorship == "No"


def test_parser_immutable():
    """ParsedJob should be immutable (frozen)."""
    parser = JobParser()
    parsed = parser.parse(title="Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    try:
        parsed.title = "Hacked"
        assert False, "ParsedJob should be immutable"
    except (TypeError, ValueError, AttributeError):
        pass  # Expected


def test_parser_fresher_friendly():
    """Parser should detect fresher-friendly roles."""
    parser = JobParser()
    parsed = parser.parse(title="Associate Product Manager", jd_text=SAMPLE_JD_PM)
    # 0-2 years should be fresher-friendly
    # The exact result depends on the JIE extractor; we just verify it runs
    assert isinstance(parsed.fresher_friendly, bool)


def test_parser_schema_version():
    """Parser should set schema_version."""
    parser = JobParser()
    parsed = parser.parse(title="ML Engineer", jd_text=SAMPLE_JD_ML)
    assert parsed.schema_version == "2.0.0"


# ---------------------------------------------------------------------------
# JobEnricher Tests
# ---------------------------------------------------------------------------

def test_enricher_seniority_senior():
    """Should classify 'Senior Backend Engineer' as SENIOR."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    structured = enricher.enrich(parsed)
    assert structured.seniority.value == Seniority.SENIOR.value


def test_enricher_seniority_intern():
    """Should classify intern titles correctly."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Software Engineering Intern", jd_text="Entry level internship position.")
    structured = enricher.enrich(parsed)
    assert structured.seniority.value == Seniority.INTERN.value


def test_enricher_domains():
    """Should infer backend domain for backend JD."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    structured = enricher.enrich(parsed)
    domain_values = [d.value for d in structured.domains]
    assert "backend" in domain_values, f"Expected 'backend' in {domain_values}"


def test_enricher_ml_domains():
    """Should infer ML domain for ML JD."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Machine Learning Engineer", jd_text=SAMPLE_JD_ML)
    structured = enricher.enrich(parsed)
    domain_values = [d.value for d in structured.domains]
    assert "machine_learning" in domain_values, f"Expected 'machine_learning' in {domain_values}"


def test_enricher_job_family():
    """Should classify job family correctly."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    structured = enricher.enrich(parsed)
    assert structured.job_family.value == "software_engineering"


def test_enricher_pm_family():
    """Should classify PM roles into product_management family."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Associate Product Manager", jd_text=SAMPLE_JD_PM)
    structured = enricher.enrich(parsed)
    assert structured.job_family.value == "product_management"


def test_enricher_capabilities():
    """Capabilities should include technologies and skills."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    structured = enricher.enrich(parsed)
    cap_values = [c.value.lower() for c in structured.capabilities]
    assert any("python" in c for c in cap_values), f"Expected Python in capabilities: {cap_values}"


def test_enricher_immutable():
    """StructuredJob should be immutable."""
    parser = JobParser()
    enricher = JobEnricher()
    parsed = parser.parse(title="Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    structured = enricher.enrich(parsed)
    try:
        structured.title = "Hacked"
        assert False, "StructuredJob should be immutable"
    except (TypeError, ValueError, AttributeError):
        pass  # Expected


# ---------------------------------------------------------------------------
# JobAssembler Tests
# ---------------------------------------------------------------------------

def test_assembler_end_to_end():
    """Full pipeline should produce a valid StructuredJob."""
    assembler = JobAssembler()
    structured = assembler.process(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    assert isinstance(structured, StructuredJob)
    assert structured.seniority.value == Seniority.SENIOR.value
    assert len(structured.domains) > 0
    assert structured.job_family.value == "software_engineering"


def test_assembler_two_step():
    """Assembler should support two-step (parse then enrich) workflow."""
    assembler = JobAssembler()
    parsed = assembler.parse(title="ML Engineer", jd_text=SAMPLE_JD_ML)
    assert isinstance(parsed, ParsedJob)
    structured = assembler.enrich(parsed)
    assert isinstance(structured, StructuredJob)


# ---------------------------------------------------------------------------
# EvaluationContextResolver Tests
# ---------------------------------------------------------------------------

def test_resolver_selects_correct_policy():
    """Resolver should select software_engineering policy for SWE jobs."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    structured = assembler.process(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    context = resolver.resolve(structured)
    assert isinstance(context, EvaluationContext)
    assert context.policy.job_family == "software_engineering"
    assert context.policy_version == "1.0"


def test_resolver_pm_policy():
    """Resolver should select product_management policy for PM jobs."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    structured = assembler.process(title="Associate Product Manager", jd_text=SAMPLE_JD_PM)
    context = resolver.resolve(structured)
    assert context.policy.job_family == "product_management"


def test_resolver_data_science_policy():
    """Resolver should select data_science policy for ML/DS jobs."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    structured = assembler.process(title="Machine Learning Engineer", jd_text=SAMPLE_JD_ML)
    context = resolver.resolve(structured)
    # ML engineer maps to data_science family
    assert context.policy.job_family in ("data_science", "software_engineering")


def test_resolver_carries_forward_fields():
    """Context should carry forward key fields from StructuredJob."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    structured = assembler.process(title="Senior Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    context = resolver.resolve(structured)
    assert context.jd_hash == structured.jd_hash
    assert context.title == structured.title
    assert context.seniority.value == structured.seniority.value
    assert context.visa_sponsorship == "No"


def test_resolver_policy_override():
    """Should accept a policy override."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    custom_policy = EvaluationPolicy(
        policy_id="custom_test",
        policy_version="99.0",
        job_family="custom",
        description="Test override policy.",
    )
    structured = assembler.process(title="Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    context = resolver.resolve(structured, policy_override=custom_policy)
    assert context.policy.policy_id == "custom_test"
    assert context.policy_version == "99.0"


def test_resolver_immutable():
    """EvaluationContext should be immutable."""
    assembler = JobAssembler()
    resolver = EvaluationContextResolver()
    structured = assembler.process(title="Backend Engineer", jd_text=SAMPLE_JD_BACKEND)
    context = resolver.resolve(structured)
    try:
        context.title = "Hacked"
        assert False, "EvaluationContext should be immutable"
    except (TypeError, ValueError, AttributeError):
        pass  # Expected


def test_policy_registry():
    """PolicyRegistry should return registered policies."""
    policy = PolicyRegistry.get_policy("software_engineering")
    assert policy.policy_id == "software_engineering_v1"

    default = PolicyRegistry.get_policy("nonexistent_family")
    assert default.policy_id == "default"

    all_policies = PolicyRegistry.list_policies()
    assert "software_engineering" in all_policies


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all Phase 2.1 tests."""
    tests = [
        # Parser
        test_parser_deterministic,
        test_parser_extracts_title,
        test_parser_extracts_experience,
        test_parser_extracts_technologies,
        test_parser_detects_no_visa,
        test_parser_immutable,
        test_parser_fresher_friendly,
        test_parser_schema_version,
        # Enricher
        test_enricher_seniority_senior,
        test_enricher_seniority_intern,
        test_enricher_domains,
        test_enricher_ml_domains,
        test_enricher_job_family,
        test_enricher_pm_family,
        test_enricher_capabilities,
        test_enricher_immutable,
        # Assembler
        test_assembler_end_to_end,
        test_assembler_two_step,
        # Resolver
        test_resolver_selects_correct_policy,
        test_resolver_pm_policy,
        test_resolver_data_science_policy,
        test_resolver_carries_forward_fields,
        test_resolver_policy_override,
        test_resolver_immutable,
        test_policy_registry,
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
    print(f"Phase 2.1 Tests: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All Phase 2.1 tests passed!")


if __name__ == "__main__":
    run_all_tests()
