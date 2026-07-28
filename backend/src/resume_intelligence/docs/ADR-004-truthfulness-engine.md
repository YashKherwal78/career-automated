"""
Architecture Decision Record 004: Strict Truthfulness & Anti-Hallucination Engine.
"""

# ADR-004: Strict Truthfulness & Anti-Hallucination Engine

## Status
Accepted

## Context
Generative AI models tend to introduce unverified technologies, dates, metrics, or companies when rewriting resume bullets or generating summaries.

## Decision
Implement a **Truthfulness Engine** (`TruthfulnessEngine`) that builds a fact index from the `CanonicalCandidateProfile`. Every AI-generated summary, bullet rewrite, or section order MUST pass AST-level set membership verification against the fact index before acceptance.

### Enforcement Rules:
- Reject any generated statement containing unverified metrics/numbers.
- Reject any statement introducing unverified companies, skills, or dates.
- Fallback automatically to original canonical text upon violation.

## Consequences
- Guaranteed zero-hallucination guarantee across all tailored resume assets.
