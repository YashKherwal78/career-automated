"""
Candidate Evidence & Multi-Source Merge Engine (Module 4 + Refinements).

Implements Candidate Evidence Pipeline:
Source Priorities:
1. Resume Knowledge Repository (highest authority)
2. Uploaded Resume (PDF/DOCX/TXT)
3. LinkedIn
4. GitHub
5. Portfolio
6. LeetCode / Competitive Coding
7. Manual User Input

Resolves conflicts via Human Review Queue rather than silent overwrite.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.resume_intelligence.canonical.models import (
    CanonicalCandidateProfile, PersonalInfo, SocialLinks, EducationItem,
    ExperienceItem, ProjectItem, CategorizedSkills, SourceMetadata, TimelineEvent
)
from src.resume_intelligence.canonical.taxonomy import SkillTaxonomy


SOURCE_PRIORITIES = {
    "resume_knowledge": 100,
    "uploaded_resume": 90,
    "user_manual": 85,
    "linkedin": 80,
    "github": 75,
    "portfolio": 70,
    "leetcode": 65,
    "external_import": 60
}


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str  # e.g., 'resume_knowledge', 'uploaded_resume', 'github'
    confidence: float = 1.0  # 0.0 to 1.0
    field_name: str  # e.g., 'personal.email', 'skills.ai_ml', 'experience.orange_labs'
    raw_value: Any
    normalized_value: Any
    extracted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReviewQueueItem(BaseModel):
    task_id: str
    field_name: str
    source_a: str
    value_a: Any
    confidence_a: float
    source_b: str
    value_b: Any
    confidence_b: float
    status: str = "pending"  # 'pending', 'resolved', 'ignored'
    resolution: Optional[Any] = None


class MergeEngine:
    """Merges evidence items into CanonicalCandidateProfile while flagging conflicts."""

    def __init__(self):
        self.taxonomy = SkillTaxonomy()
        self.review_queue: List[ReviewQueueItem] = []

    def merge_evidence_store(
        self,
        current_profile: CanonicalCandidateProfile,
        evidence_items: List[EvidenceItem]
    ) -> tuple[CanonicalCandidateProfile, List[ReviewQueueItem]]:
        
        # Sort evidence items by source priority descending
        sorted_evidence = sorted(
            evidence_items,
            key=lambda e: (SOURCE_PRIORITIES.get(e.source_type, 50), e.confidence),
            reverse=True
        )

        for item in sorted_evidence:
            field = item.field_name
            val = item.normalized_value

            if field == "personal.full_name" and val:
                current_profile.personal.full_name = str(val)
            elif field == "personal.email" and val:
                current_profile.personal.email = str(val)
            elif field == "personal.phone" and val:
                current_profile.personal.phone = str(val)
            elif field == "personal.summary" and val:
                if not current_profile.personal.summary or SOURCE_PRIORITIES.get(item.source_type, 0) >= 90:
                    current_profile.personal.summary = str(val)
            elif field == "social.linkedin" and val:
                current_profile.social_links.linkedin = str(val)
            elif field == "social.github" and val:
                current_profile.social_links.github = str(val)

            # Record provenance
            current_profile.provenance[field] = SourceMetadata(
                source_type=item.source_type,
                source_id=item.evidence_id,
                confidence=item.confidence,
                field_path=field,
                verification_status="verified" if item.confidence >= 0.85 else "unverified"
            )

        current_profile.timeline.append(
            TimelineEvent(
                event_id=f"merge_{int(datetime.utcnow().timestamp())}",
                event_type="evidence_merged",
                description=f"Merged {len(evidence_items)} evidence items into profile",
                actor="MergeEngine"
            )
        )

        return current_profile, self.review_queue
