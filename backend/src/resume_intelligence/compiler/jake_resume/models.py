"""
Structured Resume Interface for Compiler Consumption.

This model is pure presentation data — completely decoupled from AI reasoning or raw text parsing.
It strictly represents a clean, ready-to-render resume.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StructuredContact(BaseModel):
    phone: str = ""
    email: str = ""
    linkedin: str = ""
    github: str = ""
    location: str = ""
    portfolio: Optional[str] = None


class StructuredEducation(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: str
    end_date: str
    location: str = ""
    gpa: Optional[str] = None


class StructuredExperience(BaseModel):
    company: str
    title: str
    location: str = ""
    start_date: str
    end_date: str
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class StructuredProject(BaseModel):
    title: str
    technologies: List[str] = Field(default_factory=list)
    date: str = ""
    bullets: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class StructuredSkillCategory(BaseModel):
    category_name: str
    skills: List[str] = Field(default_factory=list)


class StructuredSection(BaseModel):
    section_id: str  # 'education', 'experience', 'projects', 'skills', 'summary'
    title: str
    items: List[Any] = Field(default_factory=list)


class StructuredResume(BaseModel):
    name: str
    contact: StructuredContact
    summary: Optional[str] = None
    education: List[StructuredEducation] = Field(default_factory=list)
    experience: List[StructuredExperience] = Field(default_factory=list)
    projects: List[StructuredProject] = Field(default_factory=list)
    skill_categories: List[StructuredSkillCategory] = Field(default_factory=list)
    
    # Dynamic section ordering defined by Recommendation Engine
    section_order: List[str] = Field(default_factory=lambda: ["education", "experience", "projects", "skills"])
