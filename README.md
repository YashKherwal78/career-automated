# CareerAutomated Development Runtime

This repository contains the complete CareerAutomated crawling and discovery pipeline, including backend APIs and the dashboard UI. To make starting, monitoring, and managing the development environment easy, a **tmux-based runtime** is provided.

---

## Why Tmux for Local Development?
Unlike `nohup` (which detaches processes blindly and leaves them running without easy stdout/stderr access or clean cleanup), `tmux` runs a persistent background server that:
- **Maintains Session State**: Even if you close your terminal window or lose connection, your pipelines, API server, and front-end remain active.
- **Provides Interactive Shells**: You get dedicated windows for live logs, an active SQLite database terminal, and a real-time monitor panel.
- **Simplifies Process Lifecycles**: Spawning, checking PIDs, and gracefully killing the entire process tree is centralized.

---

## Developer Commands

The project includes a `Makefile` at the root directing to helper scripts in `scripts/`:

### 1. Start Environment
To spin up all services, pipelines, and workers in a detached tmux session:
```bash
make dev
# Or run: ./scripts/dev.sh
```

### 2. Attach to Session
To view the running processes and access the windows:
```bash
make attach
# Or run: ./scripts/attach.sh
```

### 3. Detach from Session
To exit the tmux view while keeping all pipelines running in the background, press:
```text
Ctrl + B, then D
```

### 4. Restart Session
To perform a clean stop of all active runtimes and start fresh:
```bash
make restart
# Or run: ./scripts/restart.sh
```

### 5. Stop Session
To gracefully kill the scheduler, workers, API, frontend instances, and clean up tmux:
```bash
make stop
# Or run: ./scripts/stop.sh
```

---

## Tmux Session Layout

The `careerautomated` session is divided into the following windows:

1. **Window 1: `pipeline`** — Displays logs from `backend/run_pipeline.py` (which manages `CompanyDiscoveryWorker`, `EndpointVerificationWorker`, `JobCrawlerWorker`, and `CleanupWorker`).
2. **Window 2: `fastapi`** — Runs uvicorn development API server on port `8000`.
3. **Window 3: `frontend`** — Runs Vite frontend developer server on port `8080`.
4. **Window 4: `worker-logs`** — Tails live stdout/stderr streams from all active pipeline workers.
5. **Window 5: `database`** — Opens an active `sqlite3` prompt targeting `backend/data/crm.db`. Handy hints for quick diagnostic queries are pre-written in this pane.
6. **Window 6: `monitoring`** — Auto-refreshes every 3 seconds to print current dashboard KPIs and worker health.

---

## Logging Locations

Subprocess outputs are redirected to files inside the `logs/` directory:
- `logs/scheduler.log` — Scheduler daemon logs
- `logs/api.log` — FastAPI server logs
- `logs/frontend.log` — React frontend compiler/Vite logs
- `logs/discovery.log` — Company Discovery worker logs
- `logs/verification.log` — Endpoint Verification worker logs
- `logs/crawler.log` — Job Sync connector logs
- `logs/cleanup.log` — Optimization worker logs

---

## Useful Tmux Shortcuts

When attached to the session:
- **Switch to Next Window**: `Ctrl + B`, then `N`
- **Switch to Previous Window**: `Ctrl + B`, then `P`
- **Select Window by Number**: `Ctrl + B`, then `<Number>` (e.g. `0` for pipeline, `4` for database)
- **Show Window List Menu**: `Ctrl + B`, then `W`
- **Scroll Logs / Enter Copy Mode**: `Ctrl + B`, then `[` (Use arrow keys to scroll, press `Q` to exit copy mode)
