"""
Architecture Decision Record 005: Resume Asset Store & Persistence.
"""

# ADR-005: Resume Asset Store & Persistence

## Status
Accepted

## Context
Previously, tailored resumes were generated on-the-fly without persistent storage, requiring expensive re-generation whenever Auto Apply or recruiters requested candidate files.

## Decision
Create a centralized **Resume Asset Store** (`ResumeAssetStore`) persisting:
- Master Resumes & Tailored Resumes (v1, v2, v3)
- Compiled PDFs, DOCXs, HTMLs
- Original uploaded resume files
- Job ID mappings and lineage

Provide single-line accessors like `best_resume(job_id)`.

## Consequences
- Instant retrieval of tailored resumes for Auto Apply and Application Tracker.
- Reusable, version-tracked resume artifacts.
