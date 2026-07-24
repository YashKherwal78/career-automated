from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EducationInfo(BaseModel):
    degrees: List[str] = Field(default_factory=list)
    fields: List[str] = Field(default_factory=list)

class ExperienceInfo(BaseModel):
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    fresher_friendly: bool = False

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
    
    title: str = ""
    company: str = ""
    job_url: str = ""
    job_id: str = ""
    location: Dict[str, str] = Field(default_factory=lambda: {"country": "", "state": "", "city": ""})
    work_mode: str = "Unknown"
    employment_type: str = "Unknown"
    
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    fresher_friendly: bool = False
    
    salary: Dict[str, Any] = Field(default_factory=lambda: {"currency": "", "minimum": None, "maximum": None, "period": ""})
    
    education: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    
    requirements: List[Requirement] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    hiring_signals: List[str] = Field(default_factory=list)
    
    visa_sponsorship: str = "Unknown"
    posted_date: Optional[str] = None
    application_deadline: Optional[str] = None
    domain: str = "Unknown"
    
    parser_metadata: Dict[str, Any] = Field(default_factory=dict)
