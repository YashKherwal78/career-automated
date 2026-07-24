from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.career_intelligence.models.common import AuditInfo, ArtifactVersion
from src.career_intelligence.models.evidence import Evidence
from src.career_intelligence.models.snapshot import ComparisonContext

class SkillComparison(BaseModel):
    score: float = 0.0
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    extra_skills: List[str] = Field(default_factory=list)
    critical_missing: List[str] = Field(default_factory=list)
    optional_missing: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class TechnologyComparison(BaseModel):
    score: float = 0.0
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    exact_matches: List[str] = Field(default_factory=list)
    semantic_matches: List[str] = Field(default_factory=list)
    alias_matches: List[str] = Field(default_factory=list)
    related_matches: List[str] = Field(default_factory=list)
    recommended_learning_order: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class ExperienceComparison(BaseModel):
    score: float = 0.0
    required_years: int = 0
    candidate_years: float = 0.0
    gap: float = 0.0
    required_domains: List[str] = Field(default_factory=list)
    matched_domains: List[str] = Field(default_factory=list)
    leadership_match: bool = False
    seniority_match: bool = False
    ownership_match: bool = False
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EducationComparison(BaseModel):
    score: float = 0.0
    required_degree: List[str] = Field(default_factory=list)
    candidate_degree: List[str] = Field(default_factory=list)
    missing_degrees: List[str] = Field(default_factory=list)
    degree_equivalent: bool = False
    field_equivalent: bool = False
    fit: bool = False
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    missing: List[str] = Field(default_factory=list)

class ProjectComparison(BaseModel):
    score: float = 0.0
    matched_projects: List[str] = Field(default_factory=list)
    relevant_projects: List[str] = Field(default_factory=list)
    irrelevant_projects: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    matched: List[str] = Field(default_factory=list)

class CertificationComparison(BaseModel):
    score: float = 0.0
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class LocationComparison(BaseModel):
    score: float = 0.0
    location_fit: bool = False
    work_mode_fit: bool = False
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class EmploymentComparison(BaseModel):
    score: float = 0.0
    employment_type_fit: bool = False
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class ResponsibilityComparison(BaseModel):
    score: float = 0.0
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class LanguageComparison(BaseModel):
    score: float = 0.0
    language_fit: bool = True
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class ComparisonResult(BaseModel):
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    generated_at: str = ""
    profile_version: str = "2.0.0"
    job_version: str = "2.0.0"

    context: ComparisonContext = Field(default_factory=ComparisonContext)

    skills: SkillComparison = Field(default_factory=SkillComparison)
    technologies: TechnologyComparison = Field(default_factory=TechnologyComparison)
    education: EducationComparison = Field(default_factory=EducationComparison)
    experience: ExperienceComparison = Field(default_factory=ExperienceComparison)
    projects: ProjectComparison = Field(default_factory=ProjectComparison)
    certifications: CertificationComparison = Field(default_factory=CertificationComparison)
    location: LocationComparison = Field(default_factory=LocationComparison)
    employment: EmploymentComparison = Field(default_factory=EmploymentComparison)
    responsibilities: ResponsibilityComparison = Field(default_factory=ResponsibilityComparison)
    languages: LanguageComparison = Field(default_factory=LanguageComparison)

    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Evidence objects list from the Evidence Engine
    evidence: List[Evidence] = Field(default_factory=list)

    class Config:
        frozen = True

# Core Match Score Output Models
class ScoreBreakdown(BaseModel):
    skills: int = 0
    technologies: int = 0
    experience: int = 0
    projects: int = 0
    education: int = 0
    location: int = 0
    employment: int = 0
    certifications: int = 0

class MatchScore(BaseModel):
    overall_score: int
    confidence: int
    grade: str
    match_level: str
    breakdown: ScoreBreakdown
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    critical_missing: List[str] = Field(default_factory=list)
    summary: str

# Gap Analysis Models
class Gap(BaseModel):
    category: str
    name: str
    priority: str # Critical, Important, Optional, Nice-to-have

class LearningRecommendation(BaseModel):
    topic: str
    resource_type: str # course, certification, project
    description: str

class GapAnalysis(BaseModel):
    overall_gap: str # Low, Medium, High
    critical_gaps: List[Gap] = Field(default_factory=list)
    important_gaps: List[Gap] = Field(default_factory=list)
    optional_gaps: List[Gap] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    missing_technologies: List[str] = Field(default_factory=list)
    missing_certifications: List[str] = Field(default_factory=list)
    experience_gap: float = 0.0
    education_gap: Optional[str] = None
    location_gap: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    learning_paths: List[LearningRecommendation] = Field(default_factory=list)
