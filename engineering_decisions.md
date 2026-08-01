# Engineering Decisions Log

This document records the rationale behind significant architectural and operational decisions for the CareerAutomated crawler platform. It captures *why* decisions were made, not just what changed.

---

## Decision #001
**Why SQLite is retained until PostgreSQL passes shadow verification.**
Migrating to PostgreSQL immediately introduces two variables simultaneously: fixing pipeline correctness bugs and changing the persistence layer. By stabilizing SQLite first, we ensure that the parser, normalizer, and scheduler logic are provably correct. When PostgreSQL is introduced, it must run in parallel as a shadow system until it achieves 100% parity with the stabilized SQLite baseline. This eliminates migration risk.

## Decision #002
**Why scheduler changes are delayed until connector correctness is verified.**
The scheduler acts as the throttle for all providers. If we fix the priority queue starvation before fixing connector crashes (e.g., SmartRecruiters) or silent normalizer drops (e.g., Workday), the crawler will aggressively schedule broken providers, resulting in millions of wasted HTTP requests and dropped jobs. We must prove all connectors can successfully extract jobs before giving them equal queue priority.

## Decision #003
**Why PostgreSQL migration preserves behavior before optimization.**
During Phase 3, the PostgreSQL implementation will strictly mirror the SQLite schema, transaction boundaries, and queue logic. We explicitly prohibit adding "new features" or "optimizations" during the migration. This allows us to guarantee parity. Optimizations (e.g., batch upserts, advanced connection pooling) can only occur *after* the cutover to production is complete.
