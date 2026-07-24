from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Capability(BaseModel):
    id: str
    name: str
    description: str = ""
    domain: str = "general"
