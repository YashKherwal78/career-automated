# ADR-004: Explainability & Recruiter Intelligence Layer

**Status**: Accepted
**Date**: 2026-07-24

## Context

Previous career matching platforms generated textual candidate summaries by prompting LLMs directly over raw job descriptions and resumes. This introduced non-determinism, hallucinations, and score-text drift where the textual summary contradicted the numerical match score.

## Decision

We separate explanation generation into a dedicated, non-mutating **Explainability Layer**:

```text
ComparisonEngine Output / ComparisonSnapshot
                      │
                      ▼
               EvidenceBuilder ──► EvidenceReport
                      │
                      ▼
            RecruiterIntelligence ──► RecruiterSummary
```

### Invariants
1. **Zero Score Mutation**: `EvidenceBuilder` and `RecruiterIntelligence` **NEVER** recompute or modify match scores. They consume immutable scores produced by `ComparisonEngine`.
2. **Faithful Reflection**: Explanations are derived strictly from `ComparisonSnapshot` and `EvidenceItem` models.
3. **Structured Recommendations**: Recruiter recommendations (`STRONG_HIRE`, `HIRE`, `CONSIDER`, `DO_NOT_ADVANCE`) are computed deterministically from score thresholds and screening status.
4. **Natural Language Boundaries**: If LLMs are used, they are restricted to formatting deterministic facts into clean text prose — never calculating scores or inventing facts.

## Structure

```text
explainability/
  models.py                   # EvidenceItem, EvidenceReport, InterviewQuestion, RecruiterSummary
  evidence_builder.py         # EvidenceBuilder
  recruiter_intelligence.py   # RecruiterIntelligence
```

## Consequences

### Positive
- **Zero Drift**: Text summaries and numerical scores are 100% aligned.
- **Auditability**: Recruiters can trace every bullet back to concrete evidence items.
- **Testability**: Explainability can be unit-tested deterministically.

## References
- `backend/src/career_intelligence/explainability/models.py`
- `backend/src/career_intelligence/explainability/evidence_builder.py`
- `backend/src/career_intelligence/explainability/recruiter_intelligence.py`
