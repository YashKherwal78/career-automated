"""
Backfill experience_min/experience_max (migration 043) for jobs that
already have an embedding -- EmbeddingBackfillWorker only computes these
going forward, for jobs it visits because they're MISSING an embedding.
Most of the 1.4M+ active jobs already had an embedding before this
session's fix, so without this script they'd never get an experience_min
at all.

Pure CPU work (JDExtractor is deterministic, no LLM/HTTP calls), so this
can run in large batches fast -- no rate limiting needed, unlike the JD
description backfills earlier tonight.

A processed row's experience_min/max can legitimately BOTH end up NULL
(no number found in the text -- common, see JDExtractor's known weak
recall on this field), which would otherwise match the same "not yet
processed" WHERE clause forever and get reprocessed every run for no
reason. --offset exists for exactly this: a full sweep advances it every
batch so it always moves through fresh rows.

Usage:
    python3 scripts/backfill_experience.py --limit 5000
    python3 scripts/backfill_experience.py --limit 5000 --offset 5000
    python3 scripts/backfill_experience.py --limit 100 --dry-run
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.db import get_connection, is_postgres  # noqa: E402
from src.discovery.jie.extractor import JDExtractor  # noqa: E402


def run(limit: int, dry_run: bool, offset: int = 0):
    extractor = JDExtractor()
    conn = get_connection()
    cur = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cur.execute(
        f"""
        SELECT job_id, title, description FROM normalized_jobs
        WHERE status = 'ACTIVE' AND embedding IS NOT NULL
          AND experience_min IS NULL AND experience_max IS NULL
          AND description IS NOT NULL AND description != ''
        ORDER BY job_id
        LIMIT {ph} OFFSET {ph}
        """,
        (limit, offset),
    )
    rows = cur.fetchall()
    rows = [dict(r) if hasattr(r, "keys") else dict(zip([c[0] for c in cur.description], r)) for r in rows]
    conn.close()

    print(f"{len(rows)} candidate rows (embedded, experience not yet extracted)")
    if not rows:
        return

    stats = {"found_min": 0, "no_number_found": 0, "error": 0}
    updates = []
    for row in rows:
        try:
            structured = extractor.extract(title=row["title"] or "", jd_text=row["description"] or "")
        except Exception as e:
            stats["error"] += 1
            print(f"  ERROR job_id={row['job_id']}: {e}")
            continue
        if structured.experience_min is not None:
            stats["found_min"] += 1
        else:
            stats["no_number_found"] += 1
        updates.append((structured.experience_min, structured.experience_max, row["job_id"]))

    print(f"done: {stats}")
    if dry_run:
        print("  (dry-run: no DB writes made)")
        return

    conn = get_connection()
    cur = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    for exp_min, exp_max, job_id in updates:
        cur.execute(
            f"UPDATE normalized_jobs SET experience_min = {ph}, experience_max = {ph} WHERE job_id = {ph}",
            (exp_min, exp_max, job_id),
        )
    conn.commit()
    conn.close()
    print(f"  wrote {len(updates)} rows (NULL experience_min written explicitly -- means 'no number found', not 'not yet processed')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.limit, args.dry_run, args.offset)
