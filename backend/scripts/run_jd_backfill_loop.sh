#!/bin/bash
# Walks the full stale-description backlog per provider using OFFSET-based
# pagination -- NOT plain repeated LIMIT calls. Rows that fail to fetch a
# description stay in the WHERE-empty set, so LIMIT alone would keep
# returning the exact same top rows forever and the loop would grind on
# permanently-dead postings without making progress. offset advances by
# BATCH every iteration regardless of hit rate, so the loop always moves
# forward through the backlog and terminates when it runs out of rows.
set -uo pipefail

# phenom/eightfold/avature deliberately excluded: dry-run tested at <10%
# real hit rate (per-tenant HTML/JSON-LD structure varies too much for a
# single selector, and combined volume is small -- 1.5K/298/14K jobs).
PER_JOB_PROVIDERS=(workday smartrecruiters icims oracle jazzhr bamboohr rippling join_com)
BOARD_WIDE_PROVIDERS=(pinpoint recruiterbox successfactors)

BATCH=500
MAX_ITERS=2000
LOG=/app/jd_backfill.log

echo "$(date -u +%FT%TZ) starting JD backfill loop" >> "$LOG"

for provider in "${PER_JOB_PROVIDERS[@]}"; do
  offset=0
  i=0
  while [ $i -lt $MAX_ITERS ]; do
    out=$(python3 scripts/backfill_jd_descriptions.py --provider "$provider" --limit $BATCH --offset $offset 2>&1)
    echo "$(date -u +%FT%TZ) offset=$offset $out" >> "$LOG"
    if echo "$out" | grep -q "^\[$provider\] 0 candidate rows"; then
      echo "$(date -u +%FT%TZ) $provider backlog exhausted after $i batches (offset=$offset)" >> "$LOG"
      break
    fi
    offset=$((offset+BATCH))
    i=$((i+1))
  done
done

for provider in "${BOARD_WIDE_PROVIDERS[@]}"; do
  offset=0
  i=0
  while [ $i -lt $MAX_ITERS ]; do
    out=$(python3 scripts/backfill_board_wide_descriptions.py --provider "$provider" --limit $BATCH --offset $offset 2>&1)
    echo "$(date -u +%FT%TZ) offset=$offset $out" >> "$LOG"
    if echo "$out" | grep -q "^\[$provider\] 0 candidate rows"; then
      echo "$(date -u +%FT%TZ) $provider backlog exhausted after $i batches (offset=$offset)" >> "$LOG"
      break
    fi
    offset=$((offset+BATCH))
    i=$((i+1))
  done
done

echo "$(date -u +%FT%TZ) JD backfill loop finished" >> "$LOG"
