"""
JobAssembler — Orchestrates JobParser → JobEnricher → StructuredJob

Convenience facade that runs the full two-stage ingestion pipeline.
Consumers who need finer control can use JobParser and JobEnricher
directly.

Pipeline:
    Raw JD Text
        │
        ▼
    JobParser ──► ParsedJob
        │
        ▼
    JobEnricher ──► StructuredJob
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.career_intelligence.job_intelligence.enricher import JobEnricher
from src.career_intelligence.job_intelligence.models import ParsedJob, StructuredJob
from src.career_intelligence.job_intelligence.parser import JobParser

logger = logging.getLogger("JobAssembler")


class JobAssembler:
    """Runs the full job ingestion pipeline: parse → enrich.

    Usage:
        assembler = JobAssembler()
        structured = assembler.process(title="...", jd_text="...")
        # or, step by step:
        parsed = assembler.parse(title="...", jd_text="...")
        structured = assembler.enrich(parsed)
    """

    def __init__(self) -> None:
        self._parser = JobParser()
        self._enricher = JobEnricher()

    def parse(
        self,
        title: str,
        jd_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedJob:
        """Stage 1 only — raw extraction."""
        return self._parser.parse(title=title, jd_text=jd_text, metadata=metadata)

    def enrich(self, parsed: ParsedJob) -> StructuredJob:
        """Stage 2 only — semantic enrichment."""
        return self._enricher.enrich(parsed)

    def process(
        self,
        title: str,
        jd_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StructuredJob:
        """Full pipeline: parse then enrich.

        Args:
            title:    Raw job title.
            jd_text:  Full job description text.
            metadata: Optional hints (domain, job_url, etc.).

        Returns:
            An immutable StructuredJob ready for downstream consumption.
        """
        parsed = self.parse(title=title, jd_text=jd_text, metadata=metadata)
        structured = self.enrich(parsed)

        logger.info(
            "JobAssembler: processed jd_hash=%s → seniority=%s, domains=%d, family=%s",
            structured.jd_hash,
            structured.seniority.value,
            len(structured.domains),
            structured.job_family.value,
        )

        return structured
