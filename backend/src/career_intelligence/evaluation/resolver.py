"""
EvaluationContextResolver — Maps StructuredJob → EvaluationContext

Selects the appropriate evaluation policy for a job based on its
job family classification, then assembles the canonical EvaluationContext
that downstream components consume.

Pipeline position:
    StructuredJob
        │
        ▼
    EvaluationContextResolver
        │
        ▼
    EvaluationContext
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from src.career_intelligence.evaluation.models import (
    EvaluationContext,
    EvaluationPolicy,
)
from src.career_intelligence.job_intelligence.models import StructuredJob

logger = logging.getLogger("EvaluationContextResolver")


# ---------------------------------------------------------------------------
# Policy Registry — in-memory policy definitions
# ---------------------------------------------------------------------------

# Default policy applied when no job-family-specific policy exists
_DEFAULT_POLICY = EvaluationPolicy(
    policy_id="default",
    policy_version="1.0",
    job_family="unknown",
    description="Default balanced evaluation policy.",
    weights={
        "skills": 0.25,
        "technologies": 0.20,
        "experience": 0.20,
        "domain": 0.10,
        "education": 0.10,
        "seniority": 0.10,
        "location": 0.05,
    },
)

# Job-family-specific policies
_POLICY_REGISTRY: Dict[str, EvaluationPolicy] = {
    "software_engineering": EvaluationPolicy(
        policy_id="software_engineering_v1",
        policy_version="1.0",
        job_family="software_engineering",
        description="Emphasizes technical skills and technology stack alignment.",
        weights={
            "skills": 0.20,
            "technologies": 0.30,
            "experience": 0.20,
            "domain": 0.10,
            "education": 0.05,
            "seniority": 0.10,
            "location": 0.05,
        },
    ),
    "data_science": EvaluationPolicy(
        policy_id="data_science_v1",
        policy_version="1.0",
        job_family="data_science",
        description="Weights domain expertise and education higher for research roles.",
        weights={
            "skills": 0.20,
            "technologies": 0.15,
            "experience": 0.15,
            "domain": 0.20,
            "education": 0.15,
            "seniority": 0.10,
            "location": 0.05,
        },
    ),
    "product_management": EvaluationPolicy(
        policy_id="product_management_v1",
        policy_version="1.0",
        job_family="product_management",
        description="Domain knowledge and experience-heavy for product roles.",
        weights={
            "skills": 0.15,
            "technologies": 0.10,
            "experience": 0.25,
            "domain": 0.25,
            "education": 0.10,
            "seniority": 0.10,
            "location": 0.05,
        },
    ),
    "devops_sre": EvaluationPolicy(
        policy_id="devops_sre_v1",
        policy_version="1.0",
        job_family="devops_sre",
        description="Infrastructure and tooling emphasis for DevOps/SRE roles.",
        weights={
            "skills": 0.15,
            "technologies": 0.35,
            "experience": 0.20,
            "domain": 0.10,
            "education": 0.05,
            "seniority": 0.10,
            "location": 0.05,
        },
    ),
    "management": EvaluationPolicy(
        policy_id="management_v1",
        policy_version="1.0",
        job_family="management",
        description="Experience and seniority-heavy for engineering management.",
        weights={
            "skills": 0.10,
            "technologies": 0.10,
            "experience": 0.30,
            "domain": 0.15,
            "education": 0.05,
            "seniority": 0.25,
            "location": 0.05,
        },
    ),
}


class PolicyRegistry:
    """In-memory policy registry.

    Looks up the best evaluation policy for a given job family.
    Falls back to the default policy if no family-specific policy exists.
    """

    @staticmethod
    def get_policy(job_family: str) -> EvaluationPolicy:
        """Get the evaluation policy for a job family.

        Args:
            job_family: The classified job family string.

        Returns:
            The matching EvaluationPolicy, or the default policy.
        """
        return _POLICY_REGISTRY.get(job_family, _DEFAULT_POLICY)

    @staticmethod
    def list_policies() -> Dict[str, EvaluationPolicy]:
        """Return all registered policies."""
        return dict(_POLICY_REGISTRY)


class EvaluationContextResolver:
    """Resolves a StructuredJob into an EvaluationContext.

    Selects the appropriate policy based on job family, then builds
    the canonical EvaluationContext that all downstream components consume.

    Usage:
        resolver = EvaluationContextResolver()
        context = resolver.resolve(structured_job)
    """

    def resolve(
        self,
        job: StructuredJob,
        policy_override: Optional[EvaluationPolicy] = None,
    ) -> EvaluationContext:
        """Build an EvaluationContext from a StructuredJob.

        Args:
            job:             An immutable StructuredJob from JobEnricher.
            policy_override: Optional policy to use instead of auto-selection.

        Returns:
            An immutable EvaluationContext.
        """
        policy = policy_override or PolicyRegistry.get_policy(job.job_family.value)

        context = EvaluationContext(
            # Policy
            policy=policy,
            policy_version=policy.policy_version,
            # Identity
            jd_hash=job.jd_hash,
            title=job.title,
            company=job.company,
            # Classifications
            seniority=job.seniority,
            job_family=job.job_family,
            domains=list(job.domains),
            capabilities=list(job.capabilities),
            # Job parameters
            work_mode=job.work_mode,
            location=job.location,
            compensation=job.salary,
            employment_type=job.employment_type,
            experience_min=job.experience_min,
            experience_max=job.experience_max,
            fresher_friendly=job.fresher_friendly,
            # Qualifications
            education_required=list(job.education),
            certifications_required=list(job.certifications_required),
            technologies=list(job.technologies),
            skills=list(job.skills),
            # Legal
            visa_sponsorship=job.visa_sponsorship,
            # Traceability
            metadata={
                "enricher_version": job.enricher_version,
                "parsed_at": job.parsed_at,
            },
        )

        logger.info(
            "EvaluationContextResolver: jd_hash=%s → policy=%s (v%s), family=%s",
            context.jd_hash,
            policy.policy_id,
            policy.policy_version,
            context.job_family.value,
        )

        return context
