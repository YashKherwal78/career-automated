"""
Architecture Decision Record 006: Module 14 Resume Recommendation Engine & Explainability.
"""

# ADR-006: Resume Recommendation Engine & Explainability

## Status
Accepted

## Context
Decisions regarding project ordering, template selection, and skill emphasis were previously hardcoded directly inside bullet rewriting logic, making choices unexplainable and opaque.

## Decision
Introduce **Module 14: Resume Recommendation Engine** (`ResumeRecommendationEngine`).

The Recommendation Engine executes BEFORE tailoring, producing structured recommendations:
- `recommended_layout`: Classic, Modern, Compact
- `recommended_theme`: Blue, Minimal, Apple, Executive
- `recommended_strategy`: Software Engineer, Product Manager, Data Scientist, ML Engineer
- `explainability`: Plain-English rationale for every single decision.

## Consequences
- Clean separation of recommendation decisions from content tailoring.
- 100% explainable AI resume strategy for candidates and recruiters.
