# ADR-008: Career Strategy Engine

**Status**: Accepted
**Date**: 2026-07-24

## Context

Candidates need actionable, tactical guidance rather than generic advice like "apply everywhere". They require daily application targets, prioritized skill milestones, and company stage timing guidance.

## Decision

We introduce `CareerStrategyEngine`:

1. **Snapshot-Driven Recommendations**: Consumes immutable `RankingSnapshot`, `RoadmapPlan`, and `CandidateContext` to generate structured `StrategicAction` items.
2. **Zero Match Score Mutation**: Strategy logic derives tactical advice but **NEVER** mutates underlying comparison match scores.
3. **Structured Guidance Categories**:
   - `DAILY_TARGET`: Concrete daily application lists.
   - `SKILL_FOCUS`: Prioritized two-week learning goals.
   - `COMPANY_TARGETING`: Startup vs Enterprise company stage strategy based on candidate seniority level.

## References
- `backend/src/career_intelligence/strategy/models.py`
- `backend/src/career_intelligence/strategy/engine.py`
