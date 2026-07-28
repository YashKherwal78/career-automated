"""
Architecture Decision Record 001: Canonical Candidate Profile Platform Contract.
"""

# ADR-001: Canonical Candidate Profile Platform Contract

## Status
Accepted

## Context
The platform previously contained fragmented representations of candidate data across `career_intelligence`, `resume`, `applications`, and `discovery`. This led to data drift, silent overrides, and duplicate parsing logic.

## Decision
Elevate `CanonicalCandidateProfile` from a simple data model to a strict **Platform Contract** (`CandidateProfileContract`).

### Contract Rule
> Every subsystem MUST read from and write to the Canonical Candidate Profile strictly through defined interfaces (`CandidateProfileContract`). No module may maintain its own independent representation of candidate data.

## Consequences
- Single Source of Truth enforced platform-wide.
- Zero data drift across Resume Tailoring, Auto Apply, Career Intelligence, and Candidate Q&A.
- All candidate modifications are captured in a deterministic timeline audit log.
