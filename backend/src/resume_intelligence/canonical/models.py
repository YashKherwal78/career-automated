"""
Canonical Candidate Profile Platform Contract & Models.

This module defines the single source of truth for candidate data across the platform.
Contract Rule:
Every subsystem MUST read from and write to the Canonical Candidate Profile strictly
through defined interfaces (CandidateProfileContract). No module may maintain its own
independent representation of candidate data.
"""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime


class SourceMetadata(BaseModel):
    source_type: str = "unknown"  # e.g., 'resume_knowledge', 'resume_pdf', 'linkedin', 'github'
    source_id: str = "default"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 1.0  # 0.0 to 1.0
    field_path: str = ""
    verification_status: str = "verified"  # 'verified', 'unverified', 'user_confirmed'


class PersonalInfo(BaseModel):
    full_name: str = ""
    title: str = ""
    summary: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    citizenship: str = "India"
    work_authorization: str = "India"
    expected_full_time_ctc: str = "15,00,000 INR"
    expected_internship_stipend: str = "50,000 INR"
    salary_negotiable: bool = True
    notice_period: str = "0 Days"
    relocation_preferred: bool = True
    remote_preferred: bool = True


class SocialLinks(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    leetcode: Optional[str] = None
    codeforces: Optional[str] = None
    hackerrank: Optional[str] = None
    medium: Optional[str] = None
    devto: Optional[str] = None
    stackoverflow: Optional[str] = None
    twitter: Optional[str] = None


class EducationItem(BaseModel):
    id: str = ""
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: Optional[str] = None
    honors: List[str] = Field(default_factory=list)
    location: str = ""


class ExperienceItem(BaseModel):
    id: str = ""
    company: str = ""
    title: str = ""
    employment_type: str = "Full-time"
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    honest_depth_notes: str = ""
    talking_points: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    id: str = ""
    title: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    github_link: Optional[str] = None
    live_link: Optional[str] = None
    date: str = ""
    role_types: List[str] = Field(default_factory=list)  # e.g., ['AI', 'SDE', 'PRODUCT']
    elevator_pitch: str = ""
    key_decisions: List[str] = Field(default_factory=list)


class CategorizedSkills(BaseModel):
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    libraries: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    devops_infra: List[str] = Field(default_factory=list)
    developer_tools: List[str] = Field(default_factory=list)
    product_management: List[str] = Field(default_factory=list)
    data_analytics: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)


class CertificationItem(BaseModel):
    name: str = ""
    issuer: str = ""
    date: str = ""
    credential_id: Optional[str] = None


class PublicationItem(BaseModel):
    title: str = ""
    publisher: str = ""
    date: str = ""
    url: Optional[str] = None


class TimelineEvent(BaseModel):
    event_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str = ""  # e.g., 'profile_parsed', 'evidence_merged', 'skill_added', 'resume_tailored'
    description: str = ""
    actor: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CanonicalCandidateProfile(BaseModel):
    profile_id: str = "canonical_master"
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    education: List[EducationItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    skills: CategorizedSkills = Field(default_factory=CategorizedSkills)
    certifications: List[CertificationItem] = Field(default_factory=list)
    publications: List[PublicationItem] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    
    # Metadata & Quality
    provenance: Dict[str, SourceMetadata] = Field(default_factory=dict)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    completeness_score: float = 0.0
    quality_score: float = 0.0
    version: int = 1
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def get_all_skills_flat(self) -> List[str]:
        """Flattens all categorized skills into a single deduplicated list."""
        all_s = []
        for cat in self.skills.model_dump().values():
            if isinstance(cat, list):
                all_s.extend(cat)
        # Unique preserving order
        seen = set()
        res = []
        for s in all_s:
            if s and s.lower() not in seen:
                seen.add(s.lower())
                res.append(s)
        return res


class CandidateProfileContract:
    """Platform Contract Interface enforcing single source of truth access."""
    
    _instance: Optional[CanonicalCandidateProfile] = None

    @classmethod
    def get_profile(cls) -> CanonicalCandidateProfile:
        if cls._instance is None:
            cls._instance = CanonicalCandidateProfile()
        return cls._instance

    @classmethod
    def update_profile(cls, updated_profile: CanonicalCandidateProfile, reason: str = "System update") -> CanonicalCandidateProfile:
        cls._instance = updated_profile
        cls._instance.version += 1
        cls._instance.last_updated = datetime.utcnow().isoformat()
        cls._instance.timeline.append(
            TimelineEvent(
                event_id=f"evt_{len(cls._instance.timeline)+1}",
                event_type="profile_updated",
                description=f"Profile updated: {reason}",
                actor="CandidateProfileContract"
            )
        )
        return cls._instance
