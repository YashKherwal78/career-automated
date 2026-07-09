# CareerAutomated Engineering Principles

> These principles override implementation convenience.
> The goal is to keep CareerAutomated maintainable, production-ready, and free of architectural drift.

---

# 1. Single Source of Truth

There must NEVER be two production implementations of the same responsibility.

Examples:
- One Connector
- One Worker
- One Repository
- One Scheduler
- One Plugin
- One Queue implementation
- One Database abstraction

Creating duplicate implementations is considered a bug.

---

# 2. Mandatory Repository Discovery

Every implementation MUST begin with a repository discovery phase.

Before writing ANY code:
1. Search the entire repository.
2. Locate existing implementations.
3. Produce a discovery report.

The report must identify:
- Production implementation
- Legacy implementation
- Deprecated implementation
- Dead code
- Similar implementations

No code may be modified before this report is complete.

---

# 3. Extend Before Creating

The default action is:
Modify existing code.

NOT
Create new code.

Creating a new:
- file
- class
- connector
- adapter
- worker
- repository
- service

requires proof that an existing implementation cannot be extended.
Without this proof, creation is forbidden.

---

# 4. No Parallel Implementations

Parallel implementations are prohibited.

Forbidden examples:
❌ workday.py
❌ workday_connector.py
❌ workday_adapter.py

all solving the same responsibility.

Instead:
One production implementation.

Legacy implementations should either be:
- removed
- archived
- marked deprecated

---

# 5. Scope Guard

Every sprint has a strict scope.

Example:
Discovery Sprint

Allowed:
- Discovery plugins
- Homepage parsing
- Redirect handling
- Slug extraction

Forbidden:
- Scheduler changes
- Repository refactors
- Database redesign
- Queue redesign
- Architecture changes

Feature work must never silently evolve into architecture work.

---

# 6. Architecture Freeze

Stable architecture must not change during feature development.

Changing any of the following requires an explicit Architecture Decision Record (ADR):
- Connector interfaces
- Repository interfaces
- Scheduler
- Worker lifecycle
- Queue contracts
- Database schema
- Event contracts

Architecture changes are separate sprints.

---

# 7. Production First

Every implementation must integrate into the existing production pipeline.

Never build parallel pipelines.
Never create alternative execution paths.
All new functionality must plug into the existing runtime.

---

# 8. Runtime Validation

Static analysis is not sufficient.

Every implementation must be validated by execution.

Required evidence:
- Runtime logs
- Database state
- API responses
- Queue status
- Worker health
- Actual imports

Claims without runtime proof are considered unverified.

---

# 9. No Silent Failures

Exceptions must never be swallowed.

Every failure must:
- log the complete stack trace
- update worker metrics
- emit pipeline events
- expose failure through health monitoring

Production failures must always be observable.

---

# 10. Repository Hygiene

Every sprint ends with a repository audit.

The audit must identify:
- duplicate files
- duplicate connectors
- duplicate repositories
- duplicate workers
- dead code
- unreachable code
- unused imports
- deprecated implementations
- merge candidates

Output must classify every item as:
KEEP
MERGE
DELETE

Nothing is left ambiguous.

---

# 11. Production Verification

Every sprint must finish with proof.

Evidence required:
✓ Pipeline starts
✓ Worker health
✓ Queue health
✓ API health
✓ Database health
✓ Metrics
✓ Before vs After comparison

No sprint is complete without measurable improvement.

---

# 12. Funnel Driven Development

Development priorities are determined by pipeline bottlenecks.

Current priority order:
1. Discovery Coverage
2. Endpoint Verification
3. Crawl Coverage
4. Job Quality
5. Auto Apply
6. Referral Engine
7. Analytics
8. UI

Always fix the highest-impact funnel leak first.

---

# 13. One Responsibility Per Module

Every module must have exactly one responsibility.

Workers coordinate.
Repositories persist.
Plugins discover.
Connectors crawl.
Schedulers orchestrate.

Avoid mixing responsibilities.

---

# 14. Backward Compatibility

Production functionality must not regress.

Before merging:
- Existing workers still run
- Existing connectors still crawl
- Existing APIs still respond
- Existing jobs remain accessible

Regression is treated as a failed implementation.

---

# 15. AI Agent Rules

Before implementing anything:
✓ Read GUIDELINES.md
✓ Read ENGINEERING_PRINCIPLES.md
✓ Read ARCHITECTURE.md
✓ Search the repository
✓ Produce a discovery report
✓ Explain the implementation plan
✓ Wait for approval

Only then begin implementation.

---

# Core Philosophy

CareerAutomated should continuously converge toward a single, production-grade architecture.
The repository must never diverge into multiple competing implementations.
Every sprint should leave the codebase simpler, more unified, and easier to maintain than before.
