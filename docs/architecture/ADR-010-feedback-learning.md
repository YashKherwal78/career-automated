# ADR-010: Feedback Learning Engine

**Status**: Accepted
**Date**: 2026-07-24

## Context

System recommendations should adapt based on real candidate outcomes (OAs, recruiter screens, interviews, offers, and rejections). However, feedback algorithms must not corrupt the deterministic scoring core.

## Decision

We introduce `FeedbackLearningEngine`:

1. **Empirical Event Logging**: Tracks real candidate outcome events (`FeedbackEvent`).
2. **Ranking Policy Optimization Only**: Feedback loop refines `RankingPolicy` weights (e.g. `response_likelihood_weight`).
3. **Zero Comparison Score Mutation**: Feedback loop **NEVER** modifies deterministic `ComparisonEngine` match scores.

## References
- `backend/src/career_intelligence/feedback/models.py`
- `backend/src/career_intelligence/feedback/engine.py`
