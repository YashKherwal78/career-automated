from typing import List, Dict, Any, Optional, Protocol
from src.career_intelligence.models.comparison import ComparisonResult
from src.career_intelligence.models.evidence import Evidence
from src.career_intelligence.models.snapshot import ComparisonSnapshot
from src.career_intelligence.models.candidate import CandidateProfile
from src.discovery.jie.models import StructuredJob

class EvidenceBuilder(Protocol):
    def build_evidence(self, comparison: ComparisonResult) -> List[Evidence]:
        """Constructs explainable Evidence objects from comparison indicators."""
        ...

class SnapshotBuilder(Protocol):
    def build_snapshot(self, comparison: ComparisonResult) -> ComparisonSnapshot:
        """Constructs an immutable ComparisonSnapshot history record."""
        ...

class ComparisonPipeline(Protocol):
    def execute(self, profile: CandidateProfile, job: StructuredJob) -> ComparisonResult:
        """Coordinates: Capability Extraction -> Comparison -> Evidence -> Snapshot."""
        ...
