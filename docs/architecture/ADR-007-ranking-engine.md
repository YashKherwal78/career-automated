# ADR-007: Opportunity Ranking Engine

**Status**: Accepted
**Date**: 2026-07-24

## Context

A candidate may match 50+ open positions. Matching score alone does not determine which job a candidate should apply to *first*. Factors such as company response rate, hiring difficulty, compensation alignment, and job freshness dictate optimal application priority.

## Decision

We introduce `OpportunityRanker`:

1. **Deterministic Opportunity Scoring**: Opportunity score is calculated deterministically from:
   - Match Score (weight: 0.40)
   - Company Quality (weight: 0.15)
   - Response Likelihood (weight: 0.15)
   - Compensation Alignment (weight: 0.15)
   - Job Freshness (weight: 0.15)
2. **Zero Match Score Mutation**: `OpportunityRanker` computes `opportunity_score` for sorting, but **NEVER** mutates `comparison_match_score`.
3. **Auditability**: Produces a versioned `RankingSnapshot` detailing every `RankingFactor`.

## References
- `backend/src/career_intelligence/ranking/models.py`
- `backend/src/career_intelligence/ranking/ranker.py`
