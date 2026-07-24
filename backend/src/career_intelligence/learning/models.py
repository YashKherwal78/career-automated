from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class LearningNode(BaseModel):
    id: str                                 # Unique identifier (e.g. 'kubernetes')
    name: str                               # Canonical display name (e.g. 'Kubernetes')
    prerequisites: List[str] = Field(default_factory=list) # List of LearningNode IDs
    description: str = ""
