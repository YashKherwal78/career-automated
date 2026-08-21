# CLAUDE.md

## Production VM safety — read before running anything on `careerautomated`

**On 2026-08-20 the production VM went down for hours** because four one-time
backfill scripts (`yash-embv2-backfill`, `yash-searchvec-backfill`,
`yash-exp-backfill`, `yash-jd-backfill`) were launched as standalone Docker
containers, all running concurrently, each pinning heavy CPU/RAM with zero
pacing between batches, on a 4-vCPU / 15GB box that also runs the live app,
Postgres, Traefik, and Dokploy. One worker alone held ~7GB RAM. Full incident
writeup and root-cause trace: Claude's memory file `vm_crash_incident_2026-08-20.md`.

**VM specs**: 4 vCPU, 15GB RAM (see `docker-compose.yml` for the full running
stack — count anything you're about to add against this, not against an
assumed-larger box).

### Rules for any batch job / backfill / migration script touching this VM

1. **Never run more than one heavy batch job at a time.** Running 2+
   concurrently is what actually took the box down, independent of how
   efficient each one is individually.
2. **Every long-running batch loop must sleep between batches**, even when
   there's more work queued — not just on idle/error. A tight
   `while: pull batch -> process -> store -> repeat` loop with no pause will
   pin sustained CPU on a shared box. `embedding_backfill_worker.py` and
   `embedding_v2_backfill_worker.py` both do `time.sleep(BATCH_PACING_SECONDS)`
   (2s) after every successful batch — match that pattern for new workers.
3. **Set hard resource caps on any ad-hoc container**: `docker run --memory=Xg
   --cpus=Y ...` (or `docker update` on an existing one). Don't rely on the
   script being well-behaved as the only safety net.
4. **Use a bounded restart policy**, not `--restart=always`, for anything
   that isn't meant to run forever: `--restart=on-failure:3`. A one-time
   migration script that crash-loops forever with no cap is exactly what
   made this outage self-perpetuating across every VM reboot that day.
5. **Standalone `docker run` containers are invisible to `docker service
   ls`** (Dokploy/Swarm only shows services from `docker-compose.yml`).
   If you launch something outside compose, note it somewhere (this file,
   a memory entry, a comment in the launch script) — otherwise a future
   debugging session (human or Claude) won't find it by looking at the
   normal service list, same as what slowed down diagnosis this time.
6. **Before assuming a production outage is a code bug, DB issue, or
   networking problem: run `docker ps` and look for anything not in
   `docker-compose.yml`.** A stray long-running batch script is a fast,
   high-impact thing to rule out first — it was the actual cause here, and
   the disk-fullness / networking theories investigated first were both
   red herrings.
7. **Prefer running heavy one-time backfills during low-traffic hours**,
   and stop/pause them (`docker stop`, not `pkill` — killing the process
   just triggers the container's own restart policy) if the live site
   needs the headroom back.

See also: Claude's memory files `vm-infra-access` (SSH/access details) and
`vm-crash-incident-2026-08-20` (full incident trace) for more context.

## SQL query building — the "?" placeholder trap

**Never put a literal `?` character anywhere in a SQL query string built via
f-string in this codebase — including inside regex patterns (e.g. `Days?`,
a "one or zero" quantifier).** `CompatCursor.execute()`
(`backend/src/runtime/postgres/connection.py`) does a blind
`query.replace("?", "%s")` to translate this codebase's dialect-agnostic `?`
placeholder convention (`conn.dialect.placeholder()`) to Postgres's `%s` at
execute time. It cannot tell your placeholder `?` apart from a `?` that's
just regex/text content sitting inside a string literal — every `?` in the
whole query gets swept into `%s`, silently creating extra unbound
placeholders with no parameter behind them.

Confirmed real (2026-08-20): a `'^Posted [0-9]+ Days? Ago'` regex pattern in
`get_jobs_by_hybrid_search` broke parameter binding this way — the bug
didn't show up in a mocked/local test (the mock's fake `dialect.placeholder()`
returned `%s` directly, bypassing the translation layer entirely), only when
run against the real Postgres connection layer. **A placeholder-count check
against a mocked connection is not sufficient proof a query is correct** —
verify against the real connection/dialect layer, not just a mock, whenever
a query contains any literal `?`-prone content (regex quantifiers, JSON
paths with `?`, etc.).

If you need "optional character" regex semantics, use `{0,1}` instead of
`?` (identical POSIX-regex meaning, no collision): `Days{0,1}` not `Days?`.
