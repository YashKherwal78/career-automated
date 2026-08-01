"""
Tests for Phase 2.4 — Semantic Reasoning & Learning Planner

Tests:
  - SemanticReasoner (alias resolution, skill equivalence, prerequisite discovery, domain similarity)
  - LearningPlanner (prerequisite-first learning path, milestone effort estimation, roadmap plan)
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.join(os.path.dirname(__file__), ".."))))

from src.career_intelligence.reasoning.semantic_reasoner import SemanticReasoner
from src.career_intelligence.learning.planner import LearningPlanner
from src.career_intelligence.learning.models import RoadmapPlan, LearningPath


# ---------------------------------------------------------------------------
# SemanticReasoner Tests
# ---------------------------------------------------------------------------

def test_semantic_reasoner_aliases():
    """Reasoner should resolve skill aliases to canonical names."""
    reasoner = SemanticReasoner()
    assert reasoner.resolve_aliases("k8s") == "Kubernetes"
    assert reasoner.resolve_aliases("py") == "Python"
    assert reasoner.resolve_aliases("js") == "JavaScript"
    assert reasoner.resolve_aliases("postgresql") == "PostgreSQL"


def test_semantic_reasoner_equivalence():
    """Reasoner should identify skill equivalences."""
    reasoner = SemanticReasoner()
    assert reasoner.is_equivalent("postgres", "postgresql") is True
    assert reasoner.is_equivalent("react", "react.js") is True
    assert reasoner.is_equivalent("python", "java") is False


def test_semantic_reasoner_prerequisites():
    """Reasoner should discover prerequisite skills."""
    reasoner = SemanticReasoner()
    prereqs = reasoner.discover_prerequisites("Kubernetes")
    assert "Docker" in prereqs

    ts_prereqs = reasoner.discover_prerequisites("TypeScript")
    assert "JavaScript" in ts_prereqs


def test_semantic_reasoner_domain_similarity():
    """Reasoner should compute domain similarity scores."""
    reasoner = SemanticReasoner()
    assert reasoner.compute_domain_similarity("backend", "backend") == 1.0
    assert reasoner.compute_domain_similarity("backend", "devops") > 0.5
    assert reasoner.compute_domain_similarity("backend", "design") < 0.5


# ---------------------------------------------------------------------------
# LearningPlanner Tests
# ---------------------------------------------------------------------------

def test_learning_planner_roadmap():
    """LearningPlanner should generate a structured RoadmapPlan."""
    planner = LearningPlanner()
    cmp_res = {
        "comparison_id": "cmp_learn123",
        "missing_techs": ["Kubernetes", "Redis"],
        "missing_skills": ["System Design"],
    }

    plan = planner.plan_roadmap(cmp_res, target_role="DevOps Lead")
    assert isinstance(plan, RoadmapPlan)
    assert isinstance(plan.primary_path, LearningPath)
    assert len(plan.primary_path.milestones) > 0
    assert plan.primary_path.total_estimated_hours > 0


def test_learning_planner_prerequisite_ordering():
    """Prerequisites (e.g. Docker) must appear before missing tools (e.g. Kubernetes)."""
    planner = LearningPlanner()
    cmp_res = {
        "comparison_id": "cmp_k8s_test",
        "missing_techs": ["Kubernetes"],
        "missing_skills": [],
    }

    plan = planner.plan_roadmap(cmp_res, target_role="Cloud Engineer")
    milestone_names = [m.capability for m in plan.primary_path.milestones]

    assert "Docker" in milestone_names
    assert "Kubernetes" in milestone_names
    # Docker should be placed before Kubernetes in the learning sequence
    docker_idx = milestone_names.index("Docker")
    k8s_idx = milestone_names.index("Kubernetes")
    assert docker_idx < k8s_idx, f"Docker (idx {docker_idx}) should come before Kubernetes (idx {k8s_idx})"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all Phase 2.4 tests."""
    tests = [
        test_semantic_reasoner_aliases,
        test_semantic_reasoner_equivalence,
        test_semantic_reasoner_prerequisites,
        test_semantic_reasoner_domain_similarity,
        test_learning_planner_roadmap,
        test_learning_planner_prerequisite_ordering,
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
    print(f"Phase 2.4 Tests: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All Phase 2.4 tests passed!")


if __name__ == "__main__":
    run_all_tests()
