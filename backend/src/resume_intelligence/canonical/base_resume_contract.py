"""
Frozen Production Base Resume & Provenance Contract Model.

Implements JSON as the single source of truth for Base Resumes, preserving exact section semantics,
bullet provenance, ownership levels, and granular transformation tracking.
"""

import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OwnershipLevel(str, Enum):
    LEAD = "LEAD"          # Led, Architected, Founded, Spearheaded
    OWNER = "OWNER"        # Built, Developed, Engineered, Designed, Shipped
    CONTRIBUTOR = "CONTRIBUTOR" # Contributed to, Collaborated on, Assisted in
    SUPPORT = "SUPPORT"    # Maintained, Supported, Monitored


class BulletProvenance(BaseModel):
    original_text: str
    source_document: str = "uploaded_resume.pdf"
    source_section: str = "Experience"
    page_number: int = 1
    claimed_ownership: OwnershipLevel = OwnershipLevel.OWNER
    rewritten_text: Optional[str] = None
    rules_applied: List[str] = Field(default_factory=list)


class SemanticSectionType(str, Enum):
    SUMMARY = "SUMMARY"
    EDUCATION = "EDUCATION"
    EXPERIENCE = "EXPERIENCE"
    PROJECTS = "PROJECTS"
    LIVE_FREELANCE_PRODUCTS = "LIVE_FREELANCE_PRODUCTS"
    RESEARCH_PUBLICATIONS = "RESEARCH_PUBLICATIONS"
    SKILLS = "SKILLS"
    AWARDS_ACHIEVEMENTS = "AWARDS_ACHIEVEMENTS"
    CUSTOM = "CUSTOM"


class StructuredSectionItem(BaseModel):
    id: str = Field(default_factory=lambda: f"item_{uuid.uuid4().hex[:8]}")
    title: str
    subtitle: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    provenance_bullets: List[BulletProvenance] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticSection(BaseModel):
    section_id: str
    section_type: SemanticSectionType
    display_title: str
    items: List[StructuredSectionItem] = Field(default_factory=list)


class BaseResumeJSONContract(BaseModel):
    candidate_id: str
    version: int = 1
    name: str
    phone: str = ""
    email: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: Optional[str] = None
    summary: Optional[str] = None
    sections: List[SemanticSection] = Field(default_factory=list)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
