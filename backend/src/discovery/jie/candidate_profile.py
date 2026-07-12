from pydantic import BaseModel, Field
from typing import List, Optional
import yaml
import os

class CandidateProfile(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    years_experience: int = 0
    graduation_year: Optional[int] = None
    degree: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_allowed: bool = True
    employment_types: List[str] = Field(default_factory=list)
    minimum_salary: Optional[float] = 0.0
    willing_to_relocate: bool = True
    citizenship: Optional[str] = None
    visa_status: Optional[str] = None
    clearance: Optional[str] = None
    preferred_domains: List[str] = Field(default_factory=list)
    preferred_company_size: List[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str = None) -> "CandidateProfile":
        if not path:
            path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "candidate_profile.yaml")
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            # Fallback values
            return cls()
