# CareerAutomated Engineering Guidelines

This document defines the permanent engineering principles for CareerAutomated.

These rules take precedence over implementation convenience.

---

# 1. Reuse Before Building

Before writing any new code:

1. Search the repository.
2. Search existing abstractions.
3. Search existing workers.
4. Search existing repositories.
5. Search existing plugins.
6. Search existing APIs.
7. Search existing database tables.

Do NOT introduce a new abstraction if an existing one already solves the problem.

If uncertain, explain the current architecture before proposing changes.

---

# 2. System Architecture

CareerAutomated follows one canonical pipeline.

Company Sources
        ↓
company_identities
        ↓
DiscoveryOrchestrator
        ↓
career_endpoints
        ↓
Endpoint Verification
        ↓
ats_registry
        ↓
BoardSyncSession
        ↓
Connectors
        ↓
board_snapshots
        ↓
Normalization
        ↓
normalized_jobs
        ↓
FastAPI
        ↓
React Dashboard

Do not bypass this pipeline.

Every feature must integrate into it.

---

# 3. Database Ownership

Each table has a single responsibility.

company_identities
    Source of truth for companies.

career_endpoints
    Stores discovered candidate endpoints.

ats_registry
    Stores verified ACTIVE endpoints.

board_snapshots
    Stores archived raw ATS payloads.

normalized_jobs
    Stores normalized active jobs.

worker_states
    Stores runtime worker status.

local_queues
    Stores distributed work queues.

Never duplicate ownership.

Never create tables that overlap existing responsibilities.

---

# 4. Existing Infrastructure

Always reuse existing systems.

Discovery
- DiscoveryOrchestrator
- DiscoveryQueue

Verification
- EndpointValidationEngine
- ATSRegistry

Sync
- BoardSyncSession

Providers
- Greenhouse
- Lever
- Ashby
- Workday
- Workable

Workers
- CompanyDiscoveryWorker
- EndpointVerificationWorker
- JobCrawlerWorker
- CleanupWorker

API
- FastAPI

Frontend
- React
- TanStack Router
- Tailwind

Do not replace these systems.

Extend them.

---

# 5. Connector Standards

Every ATS connector must:

- inherit Connector
- register with ConnectorRegistry
- expose capabilities()
- expose sync()

Never create provider-specific execution paths outside ConnectorRegistry.

---

# 6. Provider Isolation

Provider-specific logic belongs ONLY inside provider plugins.

Never leak Greenhouse, Lever, Ashby, Workday, or Workable logic into:

- Scheduler
- Workers
- Orchestrators
- Repositories
- API
- Frontend

Adding a new ATS provider should only require:

- new provider
- registration

Nothing else.

---

# 7. Continuous Pipeline

Production always runs as continuously executing workers.

Workers are infinite loops.

Workers write heartbeats.

Workers checkpoint progress.

Workers must be idempotent.

Workers must survive crashes.

Workers never terminate after one batch.

Scheduler owns all worker lifecycles.

Workers never spawn themselves.

---

# 8. Runtime

The official runtime is tmux.

Never recommend nohup as the production runtime.

Development session:

careerautomated

Provide Makefile commands:

make dev

make attach

make restart

make stop

Logs are written to logs/.

Never rely on terminal scrollback.

---

# 9. Queue First

Never scan entire database tables repeatedly.

Use queues.

Discovery Queue

↓

Verification Queue

↓

Crawl Queue

↓

Application Queue

Workers consume queues.

Workers enqueue downstream work.

---

# 10. Live Data Only

Never introduce mock services unless explicitly requested.

Dashboard always consumes:

FastAPI

↓

SQLite

↓

Real pipeline

Never fabricate metrics.

Never simulate workers.

---

# 11. Architecture Principles

Prefer extending over rewriting.

Prefer composition over duplication.

Prefer plugins over conditionals.

Prefer registries over switch statements.

Prefer repositories over inline SQL.

Prefer incremental migration over large rewrites.

Stable APIs should remain backwards compatible.

---

# 12. Performance

Avoid unnecessary API calls.

Cache aggressively.

Reuse verified ATS endpoints.

Reuse registry entries.

Only use external search when free discovery fails.

Discovery priority:

Registry

↓

Homepage

↓

ATS Detection

↓

DuckDuckGo

↓

Exa

↓

Google

Never use expensive providers unless cheaper stages fail.

---

# 13. AI Components

Never build duplicate AI systems.

Reuse existing:

- Discovery
- Verification
- Ranking
- Resume Tailoring
- Company Intelligence
- Learning Pipeline

---

# 14. Long-Term Product Vision

CareerAutomated evolves in this order:

Company Discovery

↓

Endpoint Discovery

↓

Job Discovery

↓

Resume Intelligence

↓

Job Matching

↓

Application Queue

↓

One-click Apply

↓

Fully Autonomous Apply

↓

Learning & Optimization

New features should align with this roadmap.

---

# 15. Before Every Pull Request

Verify:

✓ Existing abstractions reused.

✓ No duplicated tables.

✓ No duplicated workers.

✓ No duplicated APIs.

✓ No provider leakage.

✓ Queue-based execution.

✓ Idempotent execution.

✓ Continuous runtime compatible.

✓ Dashboard uses live backend.

✓ No regression in existing pipeline.

---

# 16. Repository Pattern

Workers never execute SQL.
Workers never determine scheduling.
Workers only execute work.

Repositories own:
- selecting work
- reserving work
- committing work
- retries
- scheduling
- persistence

This rule is mandatory.

---

# 17. Long-Term Scalability

Every subsystem must be designed so it can be replaced without changing the rest of the system.
Examples:
- SQLite → PostgreSQL
- Local workers → Kubernetes workers
- Local scheduler → Temporal/Celery
- REST polling → WebSockets
- Mock services → Production APIs

Business logic must depend only on interfaces, never on concrete implementations.

---

# 18. Event-Driven Architecture

Workers must communicate through repositories and domain events, never by directly invoking one another.
Every significant state transition should emit a Pipeline Event.

Examples of domain events:
- CompanyDiscovered
- EndpointVerified
- JobsSynced
- JobsClosed
- ResumeMatched
- ApplicationQueued
- ApplicationSubmitted
- InterviewScheduled

Dashboards, notifications, analytics, Graphiti memory, and future AI agents should consume these events instead of querying worker internals. This ensures the system remains loosely coupled, observable, and horizontally scalable.

---

# 19. Architecture Documentation

`ARCHITECTURE.md` is a frozen design document.
Implementation sprints must not modify `ARCHITECTURE.md`.

If an implementation reveals that the architecture needs to change:
1. Stop the implementation.
2. Create an ADR (Architecture Decision Record).
3. Review and approve the ADR.
4. Update `ARCHITECTURE.md` only after the ADR is accepted.
5. Resume implementation.

Implementation work must never silently rewrite architecture documentation.