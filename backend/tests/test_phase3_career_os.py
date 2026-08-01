"""
Comprehensive Test Suite for Phase 3 — Career Intelligence Platform

Tests all 10 Modules:
  - Module 1: OpportunityRanker
  - Module 2: CareerStrategyEngine
  - Module 3: CompanyIntelligenceService
  - Module 4: CareerTimelineService
  - Module 5: ResumeIntelligenceAnalyzer
  - Module 6: InterviewIntelligenceGenerator
  - Module 7: ApplicationIntelligenceTracker
  - Module 8: FeedbackLearningEngine
  - Module 9: CareerMemoryStore
  - Module 10: CareerAnalyticsEngine
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.career_intelligence.ranking.models import RankingPolicy, RankingSnapshot
from src.career_intelligence.ranking.ranker import OpportunityRanker

from src.career_intelligence.strategy.models import CareerStrategy
from src.career_intelligence.strategy.engine import CareerStrategyEngine

from src.career_intelligence.company.models import CompanyProfile, CompanyRecommendation
from src.career_intelligence.company.service import CompanyIntelligenceService

from src.career_intelligence.timeline.models import CareerTimeline, ProgressReport
from src.career_intelligence.timeline.service import CareerTimelineService

from src.career_intelligence.resume.models import ResumeAudit
from src.career_intelligence.resume.analyzer import ResumeIntelligenceAnalyzer

from src.career_intelligence.interview.models import InterviewPreparationPlan
from src.career_intelligence.interview.generator import InterviewIntelligenceGenerator

from src.career_intelligence.application.models import ApplicationInsights
from src.career_intelligence.application.tracker import ApplicationIntelligenceTracker

from src.career_intelligence.feedback.models import FeedbackEvent
from src.career_intelligence.feedback.engine import FeedbackLearningEngine

from src.career_intelligence.memory.models import LongitudinalMemory
from src.career_intelligence.memory.store import CareerMemoryStore

from src.career_intelligence.analytics.models import AnalyticsReport
from src.career_intelligence.analytics.engine import CareerAnalyticsEngine

from src.career_intelligence.explainability.models import EvidenceReport, EvidenceItem
from src.career_intelligence.candidate_intelligence.models import CandidateContext
from src.career_intelligence.job_intelligence.models import Classification, Seniority


# ---------------------------------------------------------------------------
# Module 1: OpportunityRanker Tests
# ---------------------------------------------------------------------------

def test_opportunity_ranker_sorting_and_determinism():
    ranker = OpportunityRanker()
    opps = [
        {"opportunity_id": "opp1", "job_title": "Backend Eng", "company_name": "Acme", "comparison_result": {"overall_score": 70.0}, "company_quality": 0.9, "freshness_days": 1},
        {"opportunity_id": "opp2", "job_title": "Senior Backend Eng", "company_name": "TechInc", "comparison_result": {"overall_score": 95.0}, "company_quality": 0.9, "freshness_days": 1},
    ]

    snap1 = ranker.rank_opportunities(opps)
    snap2 = ranker.rank_opportunities(opps)

    assert snap1.total_opportunities_ranked == 2
    assert snap1.rankings[0].opportunity_id == "opp2"  # Higher match score ranks first
    assert snap1.rankings[0].comparison_match_score == 95.0
    assert snap1.rankings[0].opportunity_score == snap2.rankings[0].opportunity_score  # Deterministic


# ---------------------------------------------------------------------------
# Module 2: CareerStrategyEngine Tests
# ---------------------------------------------------------------------------

def test_career_strategy_engine_recommendations():
    engine = CareerStrategyEngine()
    ranker = OpportunityRanker()
    opps = [{"opportunity_id": "opp1", "job_title": "Backend Eng", "company_name": "Acme", "comparison_result": {"overall_score": 90.0}}]
    snap = ranker.rank_opportunities(opps)

    strategy = engine.generate_strategy("cand_123", snap, candidate_level="senior")
    assert isinstance(strategy, CareerStrategy)
    assert len(strategy.actions) > 0
    categories = [a.category for a in strategy.actions]
    assert "DAILY_TARGET" in categories
    assert "COMPANY_TARGETING" in categories


# ---------------------------------------------------------------------------
# Module 3: CompanyIntelligenceService Tests
# ---------------------------------------------------------------------------

def test_company_intelligence_service():
    service = CompanyIntelligenceService()
    profile = service.get_or_create_profile("Stripe", ats_provider="Greenhouse")
    assert profile.company_name == "Stripe"
    assert profile.ats_provider == "Greenhouse"

    rec = service.generate_recommendation("Stripe", match_score=88.0)
    assert isinstance(rec, CompanyRecommendation)
    assert rec.recommendation_level == "TOP_TARGET"


# ---------------------------------------------------------------------------
# Module 4: CareerTimelineService Tests
# ---------------------------------------------------------------------------

def test_career_timeline_service():
    service = CareerTimelineService()
    cand_ctx = CandidateContext(inferred_level=Classification(value=Seniority.SENIOR.value))

    service.record_snapshot("cand_123", cand_ctx, avg_score=75.0, unlocked_count=10)
    service.record_snapshot("cand_123", cand_ctx, avg_score=85.0, unlocked_count=18)

    report = service.generate_progress_report("cand_123", new_skills=["Docker"])
    assert isinstance(report, ProgressReport)
    assert report.score_delta == 10.0
    assert "Docker" in report.new_capabilities_learned

    timeline = service.get_timeline("cand_123")
    assert len(timeline.history) == 2


# ---------------------------------------------------------------------------
# Module 5: ResumeIntelligenceAnalyzer Tests
# ---------------------------------------------------------------------------

def test_resume_intelligence_analyzer():
    analyzer = ResumeIntelligenceAnalyzer()
    report = EvidenceReport(
        comparison_id="cmp_123",
        snapshot_id="snap_123",
        overall_score=85.0,
        screening_status="PASS",
        missing_capabilities=[EvidenceItem(category="missing_capability", title="Missing Technology: Kubernetes", description="Missing K8s")],
    )

    audit = analyzer.audit_resume(report)
    assert isinstance(audit, ResumeAudit)
    assert audit.ats_compatibility.overall_ats_score > 0.0
    assert "Kubernetes" in audit.missing_critical_keywords


# ---------------------------------------------------------------------------
# Module 6: InterviewIntelligenceGenerator Tests
# ---------------------------------------------------------------------------

def test_interview_intelligence_generator():
    generator = InterviewIntelligenceGenerator()
    report = EvidenceReport(
        comparison_id="cmp_123",
        snapshot_id="snap_123",
        overall_score=80.0,
        screening_status="PASS",
        missing_capabilities=[EvidenceItem(category="missing_capability", title="Missing Technology: Redis", description="Missing Redis")],
    )

    plan = generator.generate_plan(report, job_title="Senior Backend Engineer")
    assert isinstance(plan, InterviewPreparationPlan)
    assert plan.readiness_confidence >= 80.0
    all_questions = plan.question_bank.phone_screen_questions + plan.question_bank.technical_deep_dive_questions
    assert any("Redis" in q.topic for q in all_questions)


# ---------------------------------------------------------------------------
# Module 7: ApplicationIntelligenceTracker Tests
# ---------------------------------------------------------------------------

def test_application_intelligence_tracker():
    tracker = ApplicationIntelligenceTracker()
    tracker.log_application("cand_123", "Backend Eng", "Acme", comparison_score=85.0, status="RECRUITER_SCREEN")
    tracker.log_application("cand_123", "Fullstack Eng", "Beta", comparison_score=70.0, status="REJECTED", rejection_reason="Prefers 5+ yrs Java")

    insights = tracker.generate_insights("cand_123")
    assert isinstance(insights, ApplicationInsights)
    assert insights.total_applications == 2
    assert insights.interview_callback_rate == 0.50
    assert len(insights.rejection_patterns) > 0


# ---------------------------------------------------------------------------
# Module 8: FeedbackLearningEngine Tests
# ---------------------------------------------------------------------------

def test_feedback_learning_engine():
    engine = FeedbackLearningEngine()
    for i in range(5):
        engine.log_event("cand_123", f"job_{i}", outcome="INTERVIEW", matched_score=85.0)

    policy = RankingPolicy()
    adjusted_policy, adjustment = engine.optimize_ranking_policy(policy)

    assert adjusted_policy.response_likelihood_weight >= policy.response_likelihood_weight
    assert "Gradient step adjusted response weight" in adjustment.adjustment_reason


# ---------------------------------------------------------------------------
# Module 9: CareerMemoryStore Tests
# ---------------------------------------------------------------------------

def test_career_memory_store():
    store = CareerMemoryStore()
    mem = store.get_or_create_memory("cand_123")
    assert mem.candidate_id == "cand_123"

    updated = store.mark_milestone_completed("cand_123", "Master Kubernetes")
    assert "Master Kubernetes" in updated.completed_milestones

    fav_mem = store.add_favorite_company("cand_123", "Stripe")
    assert "Stripe" in fav_mem.preferences.favorite_companies


# ---------------------------------------------------------------------------
# Module 10: CareerAnalyticsEngine Tests
# ---------------------------------------------------------------------------

def test_career_analytics_engine():
    analytics = CareerAnalyticsEngine()
    report = analytics.generate_report("cand_123", match_scores=[80.0, 90.0, 70.0])

    assert isinstance(report, AnalyticsReport)
    assert report.avg_match_score == 80.0
    assert report.funnel.total_applications > 0
    assert len(report.skill_demand_trends) > 0


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    tests = [
        test_opportunity_ranker_sorting_and_determinism,
        test_career_strategy_engine_recommendations,
        test_company_intelligence_service,
        test_career_timeline_service,
        test_resume_intelligence_analyzer,
        test_interview_intelligence_generator,
        test_application_intelligence_tracker,
        test_feedback_learning_engine,
        test_career_memory_store,
        test_career_analytics_engine,
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
    print(f"Phase 3 Tests: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All Phase 3 tests passed!")


if __name__ == "__main__":
    run_all_tests()
