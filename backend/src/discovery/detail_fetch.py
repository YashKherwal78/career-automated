"""
Shared helpers for connectors that need a SECOND per-job HTTP request to get
the full job description (their list/search endpoint only returns summary
fields). None of these connectors had any rate limiting before this, so
every use of DetailFetchThrottle here is a conservative, explicit throttle
matching CrawlPolicy's existing default (rate_limit=5 req/sec) rather than
introducing new load characteristics the crawl framework wasn't already
built to tolerate.

Descriptions are cached in Redis so repeat crawl cycles (every 120s-900s
per connector) don't re-fetch the same job's detail page every time —
after the first pass, steady-state per-job requests drop to ~0 until the
cache entry expires or the job disappears from the list.
"""

import asyncio
import logging
from typing import Optional

from src.runtime.redis.redis_client import RedisClient

logger = logging.getLogger("DetailFetch")

CACHE_TTL_SECONDS = 7 * 24 * 3600  # descriptions rarely change day to day


def get_cached_description(provider: str, job_key: str) -> Optional[str]:
    try:
        client = RedisClient.get_client()
        return client.get(f"jd_cache:{provider}:{job_key}")
    except Exception:
        logger.debug("DetailFetch: cache read failed for %s/%s", provider, job_key)
        return None


def cache_description(provider: str, job_key: str, description: str) -> None:
    if not description:
        return
    try:
        client = RedisClient.get_client()
        client.set(f"jd_cache:{provider}:{job_key}", description, ex=CACHE_TTL_SECONDS)
    except Exception:
        logger.debug("DetailFetch: cache write failed for %s/%s", provider, job_key)


class DetailFetchThrottle:
    """Fixed-delay throttle awaited before each per-job detail request."""

    def __init__(self, requests_per_second: float = 5.0):
        self._min_interval = 1.0 / requests_per_second

    async def wait(self):
        await asyncio.sleep(self._min_interval)
