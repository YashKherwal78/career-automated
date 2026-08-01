# ADR-009: Career Memory & Longitudinal Profile Store

**Status**: Accepted
**Date**: 2026-07-24

## Context

A candidate's job search spans weeks and months. The system must retain long-term memory of completed learning milestones, historical application outcomes, preferred companies, and target technologies to function as a true Career Operating System.

## Decision

We introduce `CareerMemoryStore`:

1. **Longitudinal Persistence**: Stores candidate progression across sessions (`LongitudinalMemory`).
2. **Milestone & Preference Tracking**: Retains completed skill milestones, accepted/rejected jobs, and favorite company lists.
3. **Zero Match Score Mutation**: Memory data informs recommendations and strategy, but **NEVER** mutates deterministic `ComparisonEngine` match scores.

## References
- `backend/src/career_intelligence/memory/models.py`
- `backend/src/career_intelligence/memory/store.py`
