#!/bin/bash
# Pure SQL work (no Python/ML per row), so batches can be large. Runs
# until a batch updates 0 rows (backlog exhausted).
set -uo pipefail

BATCH=20000
MAX_ITERS=200
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
done

echo "$(date -u +%FT%TZ) search_vector backfill loop finished" >> "$LOG"
