from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class Identifier(BaseModel):
    id: str
    type: str

class Timestamp(BaseModel):
    iso_format: str

class Metadata(BaseModel):
    extra: Dict[str, Any] = Field(default_factory=dict)

class Score(BaseModel):
    value: float = 0.0
    reason: str = ""

class Confidence(BaseModel):
    level: float = 1.0
    reason: str = ""

class Version(BaseModel):
    major: int
    minor: int
    patch: int

    def to_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

class ArtifactVersion(BaseModel):
    parser: str = "2.0.0"
    ontology: str = "1.0.0"
    policy: str = "1.0.0"
    comparison: str = "2.0.0"
    capability: str = "1.0.0"
    algorithm: str = "3.0.0"

class AuditInfo(BaseModel):
    generated_at: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

class SourceReference(BaseModel):
    source_type: str  # 'resume', 'job_description', 'ontology'
    source_id: str
    snippet: Optional[str] = None
