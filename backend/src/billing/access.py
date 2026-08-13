"""
Shared paid-tier access check. Previously duplicated ad hoc between
tailor.py's `_has_cover_letter_access` and billing.py's `/subscription`
query (same `user_subscriptions` lookup, written twice) -- centralized here
since the auto-apply pipeline now needs the same check outside of any
request context (no `current_user`/`db` dependency injection available
from a background worker).
"""
from typing import Optional

# The product owner's own account is exempt -- same exemption tailor.py's
# cover-letter endpoint already carried.
FREE_ACCESS_EMAILS = {"yash.kherwal78@gmail.com"}


def has_paid_access(user_id: str, email: Optional[str] = None) -> bool:
    """True if this user has an active paid subscription (or is
    explicitly comped via FREE_ACCESS_EMAILS). Never raises -- a DB
    hiccup here should fail closed (no access) rather than take down
    whatever feature is gating on it."""
    if email and email in FREE_ACCESS_EMAILS:
        return True
    try:
        from src.api.db import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM public.user_subscriptions
                WHERE user_id = %s AND status = 'paid'
                ORDER BY paid_at DESC LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone() is not None
    except Exception:
        return False
