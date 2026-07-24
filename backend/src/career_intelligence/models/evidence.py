from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.career_intelligence.models.common import SourceReference

class Evidence(BaseModel):
    evidence_id: str
    evidence_type: str        # 'exact_match', 'semantic_inference', 'related_adjacent', 'missing_requirement'
    source_symbol: str
    target_symbol: str
    weight: float = 1.0
    explanation: str
    confidence: float = 1.0
    references: List[SourceReference] = Field(default_factory=list)
