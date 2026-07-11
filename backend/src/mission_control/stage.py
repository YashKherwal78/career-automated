from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class PipelineContext:
    run_id: str
    dry_run: bool = False
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        "jobs_extracted": 0,
        "jobs_deduplicated": 0,
        "jobs_rejected": 0,
        "jobs_scored": 0,
        "resumes_tailored": 0,
        "contacts_found": 0,
        "referrals_found": 0,
        "strategy_queue_size": 0,
        "errors": 0,
        "stage_times": {}
    })
    state: Dict[str, Any] = field(default_factory=dict)
    
    # Passing data between stages
    raw_jobs: List[Dict[str, Any]] = field(default_factory=list)
    normalized_jobs: List[Dict[str, Any]] = field(default_factory=list)
    deduplicated_jobs: List[Dict[str, Any]] = field(default_factory=list)
    passed_jobs: List[Dict[str, Any]] = field(default_factory=list)

class PipelineStage(ABC):
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineContext:
        """Executes the pipeline stage and updates the context."""
        pass
