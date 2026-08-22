"""
Daily usage limits for free-tier users on generation endpoints (resume
tailoring, cover letters). Paid users (has_paid_access) are never subject
to these limits -- this module is only ever consulted for free-tier
requests.

UTC-day boundary via date_trunc('day', NOW()) since nothing else in this
codebase defines a "today" convention yet -- see free_tier_usage_events
migration.
"""
from typing import Optional

from src.billing.access import has_paid_access

FREE_TIER_DAILY_LIMITS = {
    "resume_tailor": 5,
    "cover_letter": 3,
}


class UsageLimitExceeded(Exception):
    def __init__(self, event_type: str, limit: int):
        self.event_type = event_type
        self.limit = limit
        super().__init__(f"Daily limit of {limit} reached for {event_type}")


def enforce_quota(user_id: str, email: Optional[str], event_type: str) -> None:
    """Raises UsageLimitExceeded if a free-tier user has already hit
    today's limit for event_type. Read-only -- call this BEFORE running
    the expensive LLM-backed generation, so an already-exhausted quota
    fails fast instead of burning an LLM call first. Paid users skip the
    check entirely."""
    if has_paid_access(user_id, email):
        return

    limit = FREE_TIER_DAILY_LIMITS[event_type]

    from src.api.db import get_connection
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) AS count FROM public.free_tier_usage_events
            WHERE user_id = %s AND event_type = %s
              AND created_at >= date_trunc('day', NOW())
            """,
            (user_id, event_type),
        )
        row = cursor.fetchone()
        used = row["count"] if row else 0

        if used >= limit:
            raise UsageLimitExceeded(event_type, limit)


def record_usage(user_id: str, email: Optional[str], event_type: str) -> None:
    """Records one usage event -- call this AFTER generation succeeds, not
    before, so a failed tailoring/cover-letter attempt doesn't consume a
    free user's daily quota. No-op for paid users (nothing to count)."""
    if has_paid_access(user_id, email):
        return

    from src.api.db import get_connection
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO public.free_tier_usage_events (user_id, event_type)
            VALUES (%s, %s)
            """,
            (user_id, event_type),
        )
        conn.commit()


def get_remaining_usage(user_id: str, email: Optional[str], event_type: str) -> Optional[int]:
    """Returns remaining requests for today, or None if the user has no
    limit (paid tier). Used for surfacing "X left today" in the UI --
    read-only, never records a usage event."""
    if has_paid_access(user_id, email):
        return None

    limit = FREE_TIER_DAILY_LIMITS[event_type]

    from src.api.db import get_connection
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) AS count FROM public.free_tier_usage_events
            WHERE user_id = %s AND event_type = %s
              AND created_at >= date_trunc('day', NOW())
            """,
            (user_id, event_type),
        )
        row = cursor.fetchone()
        used = row["count"] if row else 0
        return max(0, limit - used)
