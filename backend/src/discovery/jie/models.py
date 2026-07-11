from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Requirement(BaseModel):
    type: str # 'skill', 'experience', 'education', 'domain'
    name: str # e.g. 'Python', 'Product Management', '5' (for experience)
    importance: str # 'REQUIRED', 'PREFERRED', 'OPTIONAL'
    confidence: float # Parser confidence
    evidence: str # The raw snippet from JD

class SkillGap(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    coverage: float = 0.0

class FitDetail(BaseModel):
    fit: bool = False
    score: float = 0.0
    reason: str = ""

class CandidateFit(BaseModel):
    experience: FitDetail = Field(default_factory=FitDetail)
    skills: SkillGap = Field(default_factory=SkillGap)
    education: FitDetail = Field(default_factory=FitDetail)
    location: FitDetail = Field(default_factory=FitDetail)
    missing_requirements: List[str] = Field(default_factory=list)
    overall_fit_score: float = 0.0

class StructuredJob(BaseModel):
    jd_hash: str
    jie_version: str
    parsed_at: str
    
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    employment_type: str = "Unknown"
    work_mode: str = "Unknown"
    domain: str = "Unknown"
    
    requirements: List[Requirement] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    hiring_signals: List[str] = Field(default_factory=list)
    
    parser_metadata: Dict[str, Any] = Field(default_factory=dict)
