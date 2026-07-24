from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class OntologyNode(BaseModel):
    id: str
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    market_demand: Optional[str] = None
    difficulty: Optional[str] = None
    popularity: Optional[str] = None
    deprecated: bool = False

class OntologyRelationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str  # 'IS_A', 'USES', 'REQUIRES', 'PREREQUISITE', 'RELATED_TO'
    weight: float = 1.0
    confidence: float = 1.0
