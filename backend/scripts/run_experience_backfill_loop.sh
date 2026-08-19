#!/bin/bash
# Sweeps backfill_experience.py across the full active-jobs table via
# OFFSET (see backfill_experience.py's docstring for why -- rows that
# come back with experience_min/max both NULL still match the "not yet
# processed" WHERE clause, so an offsetless loop would never advance).
# Pure CPU work, no network I/O, so batches are large and fast.
set -uo pipefail

BATCH=5000
MAX_ITERS=400
LOG=/app/experience_backfill.log

echo "$(date -u +%FT%TZ) starting experience backfill loop" >> "$LOG"

offset=0
i=0
while [ $i -lt $MAX_ITERS ]; do
  out=$(python3 scripts/backfill_experience.py --limit $BATCH --offset $offset 2>&1)
  echo "$(date -u +%FT%TZ) offset=$offset $out" >> "$LOG"
  if echo "$out" | grep -q "^0 candidate rows"; then
    echo "$(date -u +%FT%TZ) backlog exhausted after $i batches (offset=$offset)" >> "$LOG"
    break
  fi
  offset=$((offset+BATCH))
  i=$((i+1))
done

echo "$(date -u +%FT%TZ) experience backfill loop finished" >> "$LOG"
