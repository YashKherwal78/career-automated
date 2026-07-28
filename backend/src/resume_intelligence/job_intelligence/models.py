"""
Structured Job Description Intelligence Models (Module 15 / JIE V2).

Defines the canonical, machine-readable JSON schema for parsed Job Descriptions.
Stored on the VM and reused across all candidate applications without re-parsing.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    BONUS = "BONUS"


class ExtractedSkillItem(BaseModel):
    name: str
    normalized_name: str
    category: str  # e.g., 'programming_language', 'framework', 'database', 'ai_tools', 'product_frameworks'
    requirement_type: RequirementType = RequirementType.REQUIRED
    importance_score: float = 1.0  # 0.0 to 1.0
    frequency: int = 1


class ATSKeywordItem(BaseModel):
    keyword: str
    normalized_keyword: str
    weight: float = 1.0
    category: str = "technical"


class ResumeStrategySignals(BaseModel):
    role_type: str  # 'AI Engineer', 'Backend', 'Product Manager', 'SDE', 'Data Scientist'
    primary_domain: str  # 'AI', 'FinTech', 'SaaS', 'Marketplace', 'Developer Tools'
    summary_strategy: str  # Strategy advice for summary calibration
    bullet_strategy: str   # Strategy advice for bullet emphasis (e.g. Infrastructure, Scalability)
    preferred_ownership_style: str  # 'LEAD', 'OWNER', 'CONTRIBUTOR'
    priority_keywords: List[str] = Field(default_factory=list)
    priority_project_types: List[str] = Field(default_factory=list)


class StructuredJobProfile(BaseModel):
    job_id: str
    job_hash: str
    company_name: str
    role_title: str
    department: Optional[str] = None
    seniority: Optional[str] = None  # 'Junior', 'Mid', 'Senior', 'Lead', 'Executive'
    employment_type: Optional[str] = "Full-time"
    location: Optional[str] = None
    remote_type: Optional[str] = "Hybrid"  # 'Remote', 'Hybrid', 'Onsite'
    
    experience_years_required: Optional[str] = None  # e.g., '3-5 years'
    education_requirement: Optional[str] = None       # e.g., 'BS in CS or equivalent'
    
    required_skills: List[ExtractedSkillItem] = Field(default_factory=list)
    preferred_skills: List[ExtractedSkillItem] = Field(default_factory=list)
    ats_keywords: List[ATSKeywordItem] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    business_domains: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    
    strategy_signals: ResumeStrategySignals
    
    parsed_at: float
    schema_version: int = 2
