from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
import time

@dataclass
class Job:
    job_id: str  # Universal identifier
    company_id: str
    ats_type: str
    external_id: str  # ATS specific identifier (e.g., req ID)
    title: str
    department: str
    location: str
    employment_type: str
    workplace_type: str
    posted_date: str
    updated_date: str
    apply_url: str
    description: str
    salary: str
    currency: str
    experience_level: str
    metadata: Dict[str, Any]
    job_hash: str # Computed from title, department, location, description

@dataclass
class CrawlResult:
    jobs: List[Any] # Raw Jobs (e.g. WorkdayJob, GreenhouseJob)
    duration: float
    api_calls: int
    pages: int
    errors: int
    warnings: int
    metadata: Dict[str, Any] # Includes pagination info (etag, cursor, page_count)
