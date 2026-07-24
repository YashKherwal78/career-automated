from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from src.career_intelligence.models.common import ArtifactVersion, AuditInfo

class ComparisonContext(BaseModel):
    parser_version: str = "2.0.0"
    ontology_version: str = "1.0.0"
    weight_profile: str = "Default"
    comparison_timestamp: str = ""
    comparison_algorithm_version: str = "3.0.0"
    feature_flags: Dict[str, Any] = Field(default_factory=dict)

class ComparisonSnapshot(BaseModel):
    snapshot_id: str
    comparison_id: str
    candidate_version: str
    job_version: str
    versions: ArtifactVersion = Field(default_factory=ArtifactVersion)
    audit: AuditInfo
    hash_value: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
