from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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
