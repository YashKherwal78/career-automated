"""
Platform Integration Adapters (Module 13).

Integrates Resume Intelligence Platform with downstream platform subsystems:
- Career Intelligence
- Auto Apply
- Candidate Q&A
- Interview Intelligence
- Application Tracker
"""

from typing import Dict, Any
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile, CandidateProfileContract
from src.resume_intelligence.assets.asset_store import ResumeAssetStore, ResumeAsset


class PlatformIntegrationAdapters:
    """Adapters connecting Canonical Candidate Profile with all downstream tools."""

    def __init__(self, asset_store: Optional[ResumeAssetStore] = None):
        self.asset_store = asset_store or ResumeAssetStore()

    def get_for_career_intelligence(self) -> CanonicalCandidateProfile:
        """Returns single source of truth candidate profile for Career Intelligence."""
        return CandidateProfileContract.get_profile()

    def get_for_auto_apply(self, job_id: str) -> Dict[str, Any]:
        """Provides form field payload and best tailored resume PDF for Auto Apply execution."""
        profile = CandidateProfileContract.get_profile()
        asset = self.asset_store.best_resume(job_id)

        return {
            "full_name": profile.personal.full_name,
            "email": profile.personal.email,
            "phone": profile.personal.phone,
            "linkedin": profile.social_links.linkedin,
            "github": profile.social_links.github,
            "education_institution": profile.education[0].institution if profile.education else "",
            "degree": profile.education[0].degree if profile.education else "",
            "best_resume_pdf_path": asset.pdf_path if asset else None,
            "best_resume_docx_path": asset.docx_path if asset else None
        }

    def get_for_qa_agent(self) -> Dict[str, Any]:
        """Provides verified candidate context grounding for Candidate Q&A agent."""
        profile = CandidateProfileContract.get_profile()
        return {
            "identity": profile.personal.summary,
            "experience_highlights": [f"{e.title} at {e.company}" for e in profile.experience],
            "project_highlights": [p.title for p in profile.projects],
            "skills": profile.get_all_skills_flat()
        }
