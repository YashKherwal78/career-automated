from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Profile Ingestion Schemas
class PersonalInfo(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

class CandidateEducation(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    gpa: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None

class CandidateExperience(BaseModel):
    company: str
    role: str
    employment_type: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    current_position: bool = False
    bullet_points: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

class CandidateProject(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    github_link: Optional[str] = None
    live_link: Optional[str] = None
    skills_demonstrated: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)

class CandidateSkills(BaseModel):
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    libraries: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    developer_tools: List[str] = Field(default_factory=list)
    other: List[str] = Field(default_factory=list)

class CandidateCertification(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None

class CandidatePublication(BaseModel):
    title: str
    publisher: Optional[str] = None
    date: Optional[str] = None

class CandidateLink(BaseModel):
    label: str
    url: str

class CandidateProfile(BaseModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: Optional[str] = None
    education: List[CandidateEducation] = Field(default_factory=list)
    experience: List[CandidateExperience] = Field(default_factory=list)
    projects: List[CandidateProject] = Field(default_factory=list)
    skills: CandidateSkills = Field(default_factory=CandidateSkills)
    certifications: List[CandidateCertification] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    publications: List[CandidatePublication] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    external_links: List[CandidateLink] = Field(default_factory=list)
    location: Dict[str, str] = Field(default_factory=lambda: {"country": "", "state": "", "city": ""})

# Core Comparison Result Model (Immutable conceptually, fully populated)
class ComparisonResult(BaseModel):
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    generated_at: str = ""
    profile_version: str = "1.0.0"
    job_version: str = "1.0.0"

    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    extra_skills: List[str] = Field(default_factory=list)
    critical_missing_skills: List[str] = Field(default_factory=list)
    optional_missing_skills: List[str] = Field(default_factory=list)

    matched_technologies: List[str] = Field(default_factory=list)
    missing_technologies: List[str] = Field(default_factory=list)
    extra_technologies: List[str] = Field(default_factory=list)
    technology_categories: Dict[str, str] = Field(default_factory=dict)

    matched_projects: List[str] = Field(default_factory=list)
    relevant_projects: List[str] = Field(default_factory=list)
    irrelevant_projects: List[str] = Field(default_factory=list)

    matched_certifications: List[str] = Field(default_factory=list)
    missing_certifications: List[str] = Field(default_factory=list)

    education_fit: bool = False
    matched_degrees: List[str] = Field(default_factory=list)
    missing_degrees: List[str] = Field(default_factory=list)

    experience_required: int = 0
    experience_candidate: float = 0.0
    experience_gap: float = 0.0
    experience_fit: bool = False

    location_fit: bool = False
    work_mode_fit: bool = False
    employment_type_fit: bool = False
    language_fit: bool = False

    responsibility_matches: List[str] = Field(default_factory=list)
    responsibility_gaps: List[str] = Field(default_factory=list)

    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True # Enforces immutability after initialization!

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
