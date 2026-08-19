"""
Backfills normalized_jobs.search_vector (migration 044) for rows that
existed before the trigger was added -- the trigger only fires on INSERT
or UPDATE OF title/description, so pre-existing rows need one pass to
get their tsvector computed.

Unlike the JD-description/experience backfills, search_vector IS NULL is
a stable "not yet processed" signal here -- once set, it's never NULL
again (even an empty title+description produces an empty-but-non-NULL
tsvector via coalesce), so plain LIMIT batches (no OFFSET) are correct:
processed rows leave the NULL pool for good, the query naturally always
returns fresh unprocessed rows.

Usage:
    python3 scripts/backfill_search_vector.py --limit 20000
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.db import get_connection, is_postgres  # noqa: E402


def run(limit: int):
    conn = get_connection()
    cur = conn.cursor()
    ph = "%s" if is_postgres() else "?"
    cur.execute(
        f"""
        UPDATE normalized_jobs
        SET search_vector =
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
        WHERE job_id IN (
            SELECT job_id FROM normalized_jobs
            WHERE search_vector IS NULL
            LIMIT {ph}
        )
        """,
        (limit,),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    print(f"updated {updated} rows")
    return updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20000)
    args = parser.parse_args()
    run(args.limit)
