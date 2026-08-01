# ADR-011: Career Analytics Engine

**Status**: Accepted
**Date**: 2026-07-24

## Context

Candidates need visibility into their job application funnel conversion metrics, average match score distributions over time, and market demand for their core technical capabilities.

## Decision

We introduce `CareerAnalyticsEngine`:

1. **Funnel & Score Aggregation**: Computes conversion funnel statistics (`FunnelAnalytics`), score distribution buckets, and skill market demand trends.
2. **Zero Match Score Mutation**: Aggregates statistics without ever modifying deterministic comparison scores.
3. **Immutable Reporting**: Produces versioned `AnalyticsReport` objects.

## References
- `backend/src/career_intelligence/analytics/models.py`
- `backend/src/career_intelligence/analytics/engine.py`
