import time
import logging
from typing import List, Optional

logger = logging.getLogger("PipelineStateManager")

# Canonical Pipeline States
VALID_LIFECYCLE_STATES = {
    "DISCOVERED",
    "CLASSIFYING",
    "FAST_PATH_MATCHED",
    "VERIFICATION_PENDING",
    "VERIFYING",
    "VERIFIED",
    "CRAWL_PENDING",
    "CRAWLING",
    "NORMALIZING",
    "ACTIVE",
    # Failure states
    "VERIFICATION_FAILED",
    "CRAWL_FAILED",
    "NORMALIZATION_FAILED",
    "RATE_LIMITED",
    "BOT_BLOCKED",
    "ATS_CHANGED",
    "RETRY_PENDING",
    "MANUAL_REVIEW"
}

VALID_HEALTH_STATES = {
    "HEALTHY",
    "STALE",
    "RATE_LIMITED",
    "BOT_BLOCKED",
    "ERROR"
}

class PipelineStateManager:
    @staticmethod
    def transition(
        company_id: str,
        to_state: str,
        health_state: Optional[str] = None,
        failure_reason: Optional[str] = None,
        conn = None
    ) -> bool:
        """
        No-op temporarily to isolate validation to batching and PostgreSQL stability.
        """
        return True

    @staticmethod
    def transition_batch(
        company_ids: List[str],
        to_state: str,
        health_state: Optional[str] = None,
        failure_reason: Optional[str] = None,
        conn = None
    ) -> bool:
        """
        No-op temporarily to isolate validation to batching and PostgreSQL stability.
        """
        return True
