from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class StructuredJob:
    job_id: str
    company: str
    title: str
    raw_text: str
    experience_min: int
    experience_max: int
    mandatory_skills: List[str]
    preferred_skills: List[str]
    responsibilities: List[str]
    domain: str
    parser_confidence: float

@dataclass
class CandidateFit:
    experience_fit: bool
    missing_skills: List[str]
    covered_skills: List[str]
    hard_reject: bool
    hard_reject_reason: Optional[str]

@dataclass
class RewriteStrategy:
    priority_skills: List[str]
    priority_responsibilities: List[str]
    tone: str
    sections_to_prioritize: List[str]
    bullet_order: Dict[str, List[int]]
    rewrite_style: str

@dataclass
class EditOperation:
    action: str  # 'rewrite', 'move', 'compress', 'expand'
    project_id: str
    bullet_index: int
    new_text: Optional[str]
    from_index: Optional[int]
    to_index: Optional[int]
    reason: str
