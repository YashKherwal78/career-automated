from typing import List, Optional
import time
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities

class WellfoundProvider(BaseProvider):
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            requires_api_key=False,
            rate_limit_per_minute=10,
            supports_pagination=True,
            supports_incremental_sync=True,
            supports_remote_jobs=True,
            supports_search_filters=True
        )

    def validate_configuration(self) -> bool:
        # Might require a session cookie in the future, for now we assume it's working/mocked.
        return True

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        print("WellfoundProvider: Discovering jobs in India for APM/AI roles...")
        time.sleep(1)
        # Mocking 2 specific Wellfound jobs
        return [
            StandardJob(
                company="Zepto",
                role="Associate Product Manager",
                location="Mumbai, India",
                remote_hybrid_onsite="Onsite",
                experience_required="Entry Level",
                skills=["Product Requirement Documents", "Analytics"],
                job_description="Join our fast-paced product team.",
                ats_type="wellfound",
                application_url="https://wellfound.com/jobs/zepto-apm",
                source="wellfound_provider",
                date_posted="2026-06-27T00:00:00Z"
            ),
            StandardJob(
                company="Krutrim",
                role="Applied AI Engineer",
                location="Bengaluru, India",
                remote_hybrid_onsite="Hybrid",
                experience_required="0-2 Years",
                skills=["Python", "LLMs"],
                job_description="Build India's own LLM.",
                ats_type="wellfound",
                application_url="https://wellfound.com/jobs/krutrim-ai",
                source="wellfound_provider",
                date_posted="2026-06-27T00:00:00Z"
            )
        ]
