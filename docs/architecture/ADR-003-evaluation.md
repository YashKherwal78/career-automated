# ADR-003: Deterministic Evaluation & Internal Comparison Delegates

**Status**: Accepted
**Date**: 2026-07-24

## Context

Previous match scoring implementations mixed LLMs and heuristic weights in an unstructured manner, leading to non-deterministic scores for identical inputs. Additionally, orchestrator objects tended to grow into 2,000+ line god objects.

## Decision

1. **Scoring Determinism Invariant**:
   `ComparisonEngine` is fully deterministic for identical input states (`EvaluationContext` + `CandidateContext`). LLMs or non-deterministic layers are strictly forbidden from altering numerical match scores. If LLMs are used downstream, they generate explanations only.

2. **Decoupled Internal Delegates**:
   `ComparisonEngine` is the single public API. Internally, responsibilities are partitioned among non-public delegates (`src/career_intelligence/comparison/delegates.py`):
   - `EvaluationEngine`: Evaluates dimensional matching rules.
   - `SemanticReasoner`: Resolves capability/domain adjacencies.
   - `ScoreAggregator`: Computes policy-weighted scores.
   - `SnapshotBuilder`: Builds reproducible `ComparisonSnapshot` instances.

3. **Reproducible Snapshots**:
   Every comparison produces an immutable `ComparisonSnapshot` containing a cryptographic `hash_value` of the inputs, overall score, policy version, and audit timestamp.

## Structure

```text
ComparisonEngine (Public API)
    │
    ├── EvaluationEngine
    ├── SemanticReasoner
    ├── ScoreAggregator
    └── SnapshotBuilder
```

## Consequences

### Positive
- **Reproducibility**: Match scores can be audited and reproduced historically.
- **Maintainability**: Delegates remain small (<200 lines each) and clean.
- **Public API Stability**: Internal delegate refactorings do not break public callers.

## References
- `src/career_intelligence/comparison/engine.py`
- `src/career_intelligence/comparison/delegates.py`
