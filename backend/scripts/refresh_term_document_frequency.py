"""
Refreshes public.term_document_frequency from normalized_jobs.search_vector
using Postgres's own ts_stat(), which returns real per-lexeme document
frequency across the corpus.

Run this periodically (e.g. a weekly cron / manual invocation), NEVER on a
request path -- ts_stat() scans the whole search_vector column, which is
exactly the class of full-table-scan query that has already caused two
separate production incidents in this project (see
core/repositories/job/repository.py's vec_topk/lex_topk comments). This
script is the deliberate, controlled, one-shot place that cost is allowed
to happen, so candidate_term_selection.py never has to pay it live.
"""
import logging
import time

from src.api.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("refresh_term_document_frequency")


def refresh() -> int:
    start = time.monotonic()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT word, ndoc
            FROM ts_stat('SELECT search_vector FROM public.normalized_jobs WHERE status = ''ACTIVE'' AND search_vector IS NOT NULL')
            """
        )
        rows = cursor.fetchall()
        logger.info(f"ts_stat() returned {len(rows)} distinct terms in {time.monotonic() - start:.1f}s")

        cursor.execute("TRUNCATE public.term_document_frequency")
        cursor.executemany(
            """
            INSERT INTO public.term_document_frequency (term, doc_count, computed_at)
            VALUES (%s, %s, NOW())
            """,
            [(row["word"], row["ndoc"]) for row in rows],
        )
        conn.commit()

    logger.info(f"term_document_frequency refreshed: {len(rows)} terms, total time {time.monotonic() - start:.1f}s")
    return len(rows)


if __name__ == "__main__":
    refresh()
