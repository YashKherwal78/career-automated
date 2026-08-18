#!/bin/bash
# Repeatedly runs backfill_jd_descriptions.py in batches per provider until
# each provider reports 0 candidate rows (backlog exhausted) or a safety
# cap on iterations is hit. Meant to run unattended via nohup on the VM.
set -uo pipefail

# phenom/eightfold/avature deliberately excluded: dry-run tested at <10%
# real hit rate (per-tenant HTML/JSON-LD structure varies too much for a
# single selector, and combined volume is small -- 1.5K/298/14K jobs).
PROVIDERS=(workday smartrecruiters icims oracle jazzhr)
BATCH=500
MAX_ITERS=2000
LOG=/app/jd_backfill.log

echo "$(date -u +%FT%TZ) starting JD backfill loop" >> "$LOG"

for provider in "${PROVIDERS[@]}"; do
  i=0
  while [ $i -lt $MAX_ITERS ]; do
    out=$(python3 scripts/backfill_jd_descriptions.py --provider "$provider" --limit $BATCH 2>&1)
    echo "$(date -u +%FT%TZ) $out" >> "$LOG"
    if echo "$out" | grep -q "^\[$provider\] 0 candidate rows"; then
      echo "$(date -u +%FT%TZ) $provider backlog exhausted after $i batches" >> "$LOG"
      break
    fi
    i=$((i+1))
  done
done

echo "$(date -u +%FT%TZ) JD backfill loop finished" >> "$LOG"
