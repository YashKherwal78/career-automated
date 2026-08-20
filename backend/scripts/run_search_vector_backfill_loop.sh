#!/bin/bash
# Pure SQL work (no Python/ML per row), so batches don't need to be tiny --
# but a bare loop with zero pause between 20000-row UPDATE statements is
# exactly the "no pacing between batches" pattern CLAUDE.md now warns
# about (2026-08-20 outage) applied to sustained Postgres write/WAL load
# instead of CPU. Smaller batches + a real pause between them keeps this
# from competing with the live app's own queries on the same box.
set -uo pipefail

BATCH=5000
BATCH_PACING_SECONDS=5
MAX_ITERS=800
LOG=/app/search_vector_backfill.log

echo "$(date -u +%FT%TZ) starting search_vector backfill loop" >> "$LOG"

i=0
while [ $i -lt $MAX_ITERS ]; do
  out=$(python3 scripts/backfill_search_vector.py --limit $BATCH 2>&1)
  echo "$(date -u +%FT%TZ) $out" >> "$LOG"
  if echo "$out" | grep -q "^updated 0 rows"; then
    echo "$(date -u +%FT%TZ) backlog exhausted after $i batches" >> "$LOG"
    break
  fi
  i=$((i+1))
  sleep $BATCH_PACING_SECONDS
done

echo "$(date -u +%FT%TZ) search_vector backfill loop finished" >> "$LOG"
