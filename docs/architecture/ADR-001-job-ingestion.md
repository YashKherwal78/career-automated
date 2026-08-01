# ADR-001: Job Ingestion — Separation of Parsing from Semantic Enrichment

**Status**: Accepted
**Date**: 2026-07-24

## Context

The original JIE (Job Description Intelligence Extractor) combined raw text extraction
and semantic enrichment into a single `JDExtractor.extract()` call that produced a
monolithic `StructuredJob`. This made it impossible to:

1. Test extraction and classification independently.
2. Cache parsed results while evolving enrichment logic.
3. Swap or version enrichment strategies without re-parsing.

## Decision

Split job ingestion into two immutable stages:

```
Raw JD Text → JobParser → ParsedJob → JobEnricher → StructuredJob
```

### Stage 1: JobParser → ParsedJob
- Extracts **only explicitly present facts** from job text.
- No semantic inference, classification, or candidate awareness.
- Reuses JIE sub-extractors (experience, education, location, etc.) internally.
- Output is **immutable** (`frozen = True`).

### Stage 2: JobEnricher → StructuredJob
- Takes ParsedJob and infers **semantic classifications**:
  - Seniority level (INTERN through C_LEVEL)
  - Domains (backend, ML, etc.)
  - Capabilities (normalized technology and skill vector)
  - Job family (software_engineering, data_science, etc.)
- Each classification is wrapped in `Classification(value, confidence)`.
- Output is **immutable** (`frozen = True`).
- Enricher is **entirely candidate-agnostic**.

### EvaluationContextResolver → EvaluationContext
- Maps StructuredJob → canonical EvaluationContext.
- Selects appropriate evaluation policy from PolicyRegistry based on job family.
- Includes `policy_version` for reproducibility.
- Output is **immutable** (`frozen = True`).

## Internal Implementation Detail

`ComparisonEngine` (Phase 2.2) will internally coordinate:
- `EvaluationEngine`
- `SemanticReasoner`
- `ScoreAggregator`
- `SnapshotBuilder`

These are **internal implementation details**, not public APIs. They may be
refactored freely without changing the external architecture.

## Consequences

### Positive
- **Testability**: Each stage can be unit-tested in isolation.
- **Cacheability**: ParsedJob can be cached; enrichment can be re-run independently.
- **Versioning**: `schema_version` and `enricher_version` enable schema evolution.
- **Confidence tracking**: `Classification(value, confidence)` lets downstream consumers
  reason about enrichment certainty.

### Negative
- Slightly more code than the monolithic approach.
- Two models to maintain instead of one.

### Risks
- Sub-extractor API changes in JIE would require parser adapter updates.
  Mitigated by the parser acting as an adapter layer.

## References
- `backend/src/career_intelligence/job_intelligence/models.py`
- `backend/src/career_intelligence/job_intelligence/parser.py`
- `backend/src/career_intelligence/job_intelligence/enricher.py`
- `backend/src/career_intelligence/job_intelligence/assembler.py`
- `backend/src/career_intelligence/evaluation/resolver.py`
