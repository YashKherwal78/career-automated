"""
Pipeline B — Job Board Provider Registry.

The worker calls JobBoardRegistry.load() and loops over whatever comes back.
Adding a new provider is one line here — nothing else changes.

Providers are instantiated lazily and filtered by is_available().
"""

import logging
from typing import List
from src.discovery.providers.job_board_provider import JobBoardProvider

logger = logging.getLogger("JobBoardRegistry")

# ── Registered providers ────────────────────────────────────────────────────
# To add a new provider: append its class to _PROVIDER_CLASSES.
# To disable a provider without deleting it: comment out its line.
# CuratedRepositoryProvider is intentionally excluded here until it is ported
# to the current DB schema (company_intelligence_static no longer exists).

def _registered_classes():
    from src.discovery.providers.linkedin_board_provider import LinkedInBoardProvider
    from src.discovery.providers.google_jobs_board_provider import GoogleJobsBoardProvider
    # TODO: from src.discovery.providers.wellfound_board_provider import WellfoundBoardProvider
    # TODO: from src.discovery.providers.indeed_board_provider import IndeedBoardProvider
    # TODO (port): from src.discovery.providers.curated_repository_provider import CuratedRepositoryProvider
    return [LinkedInBoardProvider, GoogleJobsBoardProvider]


class JobBoardRegistry:
    """
    Plugin registry for Pipeline B providers.

    Usage:
        registry = JobBoardRegistry()
        for provider in registry.load():
            result = provider.discover(cursor=last_cursor)
    """

    def load(self) -> List[JobBoardProvider]:
        """
        Instantiate all registered providers, skip those that are unavailable
        (e.g. missing API keys), and return the ready list.
        """
        available = []
        for cls in _registered_classes():
            try:
                instance = cls()
                if instance.is_available():
                    available.append(instance)
                    logger.info(f"JobBoardRegistry: {instance.name} is available.")
                else:
                    logger.warning(
                        f"JobBoardRegistry: {cls.__name__} skipped — "
                        f"credentials not available (set APIFY_API_KEY to enable)."
                    )
            except Exception as e:
                logger.warning(f"JobBoardRegistry: failed to instantiate {cls.__name__}: {e}")
        return available
