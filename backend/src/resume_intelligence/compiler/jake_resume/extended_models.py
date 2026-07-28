"""
Structured Dynamic Section & Custom Section Extension Model.

Allows Jake Resume Renderer to support arbitrary custom sections (e.g. Research, Live Products, Patents, Hackathons, Open Source)
without deleting candidate content.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.resume_intelligence.compiler.jake_resume.models import (
    StructuredContact, StructuredEducation, StructuredExperience, StructuredProject, StructuredSkillCategory
)


class CustomSectionItem(BaseModel):
    title: str = ""
    subtitle: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class CustomSection(BaseModel):
    section_title: str
    items: List[CustomSectionItem] = Field(default_factory=list)


class ExtendedStructuredResume(BaseModel):
    name: str
    contact: StructuredContact
    summary: Optional[str] = None
    education: List[StructuredEducation] = Field(default_factory=list)
    experience: List[StructuredExperience] = Field(default_factory=list)
    projects: List[StructuredProject] = Field(default_factory=list)
    skill_categories: List[StructuredSkillCategory] = Field(default_factory=list)
    custom_sections: List[CustomSection] = Field(default_factory=list)
    section_order: List[str] = Field(default_factory=list)
