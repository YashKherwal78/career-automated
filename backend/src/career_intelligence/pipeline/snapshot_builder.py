import hashlib
import uuid
import datetime
from src.career_intelligence.models.comparison import ComparisonResult
from src.career_intelligence.models.snapshot import ComparisonSnapshot
from src.career_intelligence.models.common import ArtifactVersion, AuditInfo
from src.career_intelligence.pipeline.interfaces import SnapshotBuilder

class DefaultSnapshotBuilder(SnapshotBuilder):
    def build_snapshot(self, comparison: ComparisonResult) -> ComparisonSnapshot:
        """Constructs an immutable ComparisonSnapshot history record."""
        snapshot_id = str(uuid.uuid4())
        
        # Calculate comparison state hash
        hash_input = f"{comparison.candidate_id}||{comparison.job_id}||{comparison.generated_at}"
        hash_value = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        return ComparisonSnapshot(
            snapshot_id=snapshot_id,
            comparison_id=snapshot_id[:8],
            candidate_version=comparison.profile_version,
            job_version=comparison.job_version,
            versions=ArtifactVersion(),
            audit=AuditInfo(
                generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            ),
            hash_value=hash_value,
            metadata={}
        )
