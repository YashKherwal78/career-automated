# ADR-006: Learning Planner & Prerequisite Graph Traversal

**Status**: Accepted
**Date**: 2026-07-24

## Context

Candidates need actionable guidance on how to bridge skill gaps for targeted job opportunities. Recommending missing skills in isolation without accounting for prerequisite ordering (e.g. recommending Kubernetes without verifying Docker background) leads to unachievable learning paths.

## Decision

We introduce `LearningPlanner`:

1. **Prerequisite-First Roadmaps**: `LearningPlanner` delegates to `SemanticReasoner` to discover prerequisite capabilities so foundational skills are learned before advanced tools.
2. **Impact-Prioritized Milestones**: Missing capabilities are structured into `LearningMilestone` items categorized by priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and estimated effort hours.
3. **Zero Score Mutation**: `LearningPlanner` generates roadmaps derived from `ComparisonEngine` results without modifying the underlying match scores.

## Structure

```text
ComparisonEngine Output / Missing Capabilities
                       │
                       ▼
    SemanticReasoner (Prerequisite Discovery)
                       │
                       ▼
  LearningPlanner ──► RoadmapPlan (LearningPath + LearningMilestones)
```

## Consequences

### Positive
- Actionable, realistic learning paths for candidates.
- Clear effort estimation (hours) and expected eligibility gain.

## References
- `backend/src/career_intelligence/learning/models.py`
- `backend/src/career_intelligence/learning/planner.py`
