from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class OntologyNode(BaseModel):
    id: str                                 # Unique identifier (e.g. 'react')
    name: str                               # Canonical display name (e.g. 'React')
    type: str                               # 'technology', 'skill', 'role', 'domain', 'degree'
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OntologyRelationship(BaseModel):
    source_id: str
    target_id: str
    relation_type: str                      # 'is_a', 'requires', 'part_of', 'related_to'
    weight: float = 1.0
