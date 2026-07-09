"""
Pipeline B — Job Board Normalizer.

Converts a StandardJob (from any job board provider) into a CanonicalJob
using the existing ingestion contract shared with Pipeline A.

This ensures:
  - One dedup algorithm (JobIdentity.get_hash)
  - One repository (JobRepository.upsert_and_diff)
  - One diff/close strategy
  - One hash strategy

No second persistence path is created here.
"""

import time
import hashlib
import logging
from typing import Optional

from src.discovery.models import CanonicalJob, JobIdentity
from src.discovery.providers.base_provider import StandardJob
from src.discovery.pipeline.company_resolver import CompanyResolver

logger = logging.getLogger("JobBoardNormalizer")


def _url_hash(url: str) -> str:
    """Stable 16-char id derived from the canonical apply URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class JobBoardNormalizer:
    """
    Converts StandardJob → CanonicalJob.

    Uses CompanyResolver to map the company name to an existing company_id
    (or enqueue for Pipeline A if unknown). The resulting CanonicalJob is
    passed directly to JobRepository.upsert_and_diff() — no new write path.
    """

    def __init__(self, resolver: CompanyResolver):
        self.resolver = resolver

    def to_canonical(self, job: StandardJob, board_id: str) -> Optional[CanonicalJob]:
        """
        Convert a StandardJob to a CanonicalJob.

        Args:
            job:      StandardJob from a job board provider.
            board_id: Provider name used as the board identifier
                      (e.g. 'linkedin', 'google_jobs').

        Returns:
            CanonicalJob or None if the job cannot be normalized
            (e.g. missing required fields).
        """
        if not job.application_url or not job.role:
            logger.debug(f"JobBoardNormalizer: skipping job with no URL or title.")
            return None

        try:
            company_id = self.resolver.resolve(job.company, job.application_url)

            external_id = _url_hash(job.application_url)

            identity = JobIdentity(
                provider=board_id,
                board_id=board_id,
                external_job_id=external_id,
            )

            return CanonicalJob(
                identity=identity,
                company_id=company_id,
                board_id=board_id,
                title=job.role,
                description=job.job_description or "",
                location=job.location or "",
                remote_type=job.remote_hybrid_onsite or "",
                department="",
                employment_type="",
                seniority=job.experience_required or "",
                salary_min=None,
                salary_max=None,
                salary_currency="",
                posted_at=job.date_posted or "",
                apply_url=job.application_url,
                raw_payload=vars(job),
                normalized_at=time.time(),
            )
        except Exception as e:
            logger.warning(
                f"JobBoardNormalizer: failed to convert job '{job.role}' "
                f"at {job.application_url}: {e}"
            )
            return None
