"""
Architecture Decision Record 002: Candidate Evidence and Multi-Source Merge Engine.
"""

# ADR-002: Candidate Evidence & Multi-Source Merge Engine

## Status
Accepted

## Context
Raw extractions from resumes, LinkedIn, GitHub, and external repositories previously overwrote profile fields directly. When sources conflicted (e.g., resume lists Python, GitHub shows Rust), data was silently lost.

## Decision
Introduce a **Candidate Evidence Pipeline**:
`Multi-Source Ingestion -> Candidate Evidence Store -> Priority Merge Engine -> Canonical Candidate Profile`

### Priority Hierarchy:
1. `resume_knowledge` repository (Authoritative Ground Truth)
2. `uploaded_resume`
3. `user_manual`
4. `linkedin`
5. `github`
6. `leetcode`

Conflicting or low-confidence extractions bypass direct updates and spawn tasks in the **Human Review Queue**.

## Consequences
- 100% provenance and field-level confidence tracking.
- Zero silent data overwrites.
