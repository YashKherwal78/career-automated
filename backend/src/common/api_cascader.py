"""
Generic cascading-fallback pattern for "try provider A, then B, then C" —
reusable anywhere we have multiple APIs for the same capability (search,
enrichment, scraping, etc.), not just one use case.

Ordered cheapest/free-first: cheaper providers are tried first, and more
expensive ones are only reached if the cheaper ones didn't return enough
results — this isn't a plain "stop at first success" cascade, since even a
successful free-tier call might not return enough results on its own, and
isn't a "call everything and merge" fan-out either, since that would burn
paid-provider quota even when the free tier alone was already sufficient.
"""

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, List, TypeVar

logger = logging.getLogger("ApiCascader")

T = TypeVar("T")


@dataclass
class CascadeProvider(Generic[T]):
    name: str
    call: Callable[..., Awaitable[List[T]]]
    free: bool = True


class ApiCascader(Generic[T]):
    def __init__(self, providers: List[CascadeProvider[T]]):
        self.providers = providers

    async def execute(self, *args, min_results: int = 1, **kwargs) -> List[T]:
        collected: List[T] = []
        for provider in self.providers:
            try:
                results = await provider.call(*args, **kwargs)
            except Exception as e:
                logger.warning(f"[ApiCascader] {provider.name} failed: {e}")
                continue

            if results:
                collected.extend(results)
                logger.debug(
                    f"[ApiCascader] {provider.name} ({'free' if provider.free else 'paid'}) "
                    f"returned {len(results)} results (total so far: {len(collected)})"
                )

            if len(collected) >= min_results:
                break

        return collected
