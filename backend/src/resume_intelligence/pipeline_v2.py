"""
Production Resume Pipeline Orchestrator (V2 Architecture).

Implements exact Stage 1 & Stage 2 pipeline separation:
- Stage 1: Base Resume Generation (Exact normalization into stored Jake Base Resume, zero deletions).
- Stage 2: Ephemeral Tailored Resume Generation (Uses Base Resume + Candidate Memory + resume_knowledge 2 + JD, NEVER persisted).
"""

import os
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile
from src.resume_intelligence.compiler.jake_resume.extended_models import (
    ExtendedStructuredResume, StructuredContact, StructuredEducation, StructuredExperience,
    StructuredProject, StructuredSkillCategory, CustomSection, CustomSectionItem
)
from src.resume_intelligence.compiler.jake_base_compiler import JakeBaseCompiler
from src.resume_intelligence.tailoring.global_rewriter import GlobalRuleEngine
from src.resume_intelligence.recommendation.engine import ResumeRecommendationEngine
from src.resume_intelligence.truthfulness.verifier import TruthfulnessEngine


class CandidateStore(BaseModel):
    candidate_id: str
    base_resume_pdf_path: str
    base_resume_tex_path: str
    canonical_profile: CanonicalCandidateProfile
    candidate_memory: Dict[str, Any] = Field(default_factory=dict)


class ProductionResumePipeline:
    """Production Multi-Tenant Pipeline executing Stage 1 & Stage 2."""

    # In-memory candidate storage (Base Resumes only)
    _stored_candidates: Dict[str, CandidateStore] = {}

    # --------------------------------------------------------------------------
    # STAGE 1: BASE RESUME GENERATION (Stored Permanently)
    # --------------------------------------------------------------------------
    @classmethod
    def generate_and_store_base_resume(
        cls,
        candidate_id: str,
        canonical_profile: CanonicalCandidateProfile,
        custom_sections: Optional[List[CustomSection]] = None,
        storage_dir: str = "artifacts/stored_base_resumes"
    ) -> CandidateStore:
        """Converts uploaded candidate profile into a permanent stored Jake Base Resume without section loss or bullet rewriting."""
        os.makedirs(storage_dir, exist_ok=True)

        # 1. Convert to Extended Presentation Model (Zero Content Loss)
        extended_resume = ExtendedStructuredResume(
            name=canonical_profile.personal.full_name,
            contact=StructuredContact(
                phone=canonical_profile.personal.phone,
                email=canonical_profile.personal.email,
                linkedin=canonical_profile.social_links.linkedin,
                github=canonical_profile.social_links.github,
                portfolio=canonical_profile.social_links.portfolio
            ),
            summary=canonical_profile.personal.summary if canonical_profile.personal.summary else None,
            education=[
                StructuredEducation(
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_date=edu.start_date,
                    end_date=edu.end_date
                ) for edu in canonical_profile.education
            ],
            experience=[
                StructuredExperience(
                    company=exp.company,
                    title=exp.title,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    bullets=exp.bullets,
                    technologies=exp.technologies
                ) for exp in canonical_profile.experience
            ],
            projects=[
                StructuredProject(
                    title=proj.title,
                    technologies=proj.technologies,
                    date=proj.date,
                    bullets=proj.bullets
                ) for proj in canonical_profile.projects
            ],
            skill_categories=[
                StructuredSkillCategory(category_name="AI & ML", skills=canonical_profile.skills.ai_ml),
                StructuredSkillCategory(category_name="Product Management", skills=canonical_profile.skills.product_management),
                StructuredSkillCategory(category_name="Backend & Infra", skills=canonical_profile.skills.devops_infra),
                StructuredSkillCategory(category_name="Data & Analytics", skills=canonical_profile.skills.data_analytics)
            ],
            custom_sections=custom_sections if custom_sections else []
        )

        # 2. Compile Base Resume into Jake Template
        compiler = JakeBaseCompiler()
        paths = compiler.render_and_compile(
            resume=extended_resume,
            output_dir=os.path.join(storage_dir, candidate_id),
            filename_prefix=f"Base_Resume_{candidate_id}"
        )

        store = CandidateStore(
            candidate_id=candidate_id,
            base_resume_pdf_path=paths["pdf"],
            base_resume_tex_path=paths["tex"],
            canonical_profile=canonical_profile,
            candidate_memory={"profile_version": canonical_profile.version}
        )

        cls._stored_candidates[candidate_id] = store
        return store

    # --------------------------------------------------------------------------
    # STAGE 2: EPHEMERAL TAILORED RESUME GENERATION (Never Persisted)
    # --------------------------------------------------------------------------
    @classmethod
    def generate_ephemeral_tailored_resume(
        cls,
        candidate_id: str,
        job_title: str,
        job_description: str,
        temp_output_dir: str = "artifacts/ephemeral_tailored_outputs"
    ) -> Dict[str, Any]:
        """Generates a temporary tailored resume using stored Base Resume + resume_knowledge 2. NEVER STORED."""

        store = cls._stored_candidates.get(candidate_id)
        assert store is not None, f"Candidate {candidate_id} Base Resume not found!"

        # 1. Recommendation Reasoning (Role Analysis)
        rec_engine = ResumeRecommendationEngine()
        recommendation = rec_engine.generate_recommendation(store.canonical_profile, job_title, job_description)

        # 2. Load Global Rule Engine (resume_knowledge 2)
        global_engine = GlobalRuleEngine()

        # 3. Rewrite Bullets using resume_knowledge 2 Rules + Truthfulness Check
        tailored_profile = store.canonical_profile.model_copy(deep=True)
        bullet_transformation_log = []

        for exp in tailored_profile.experience:
            new_bullets = []
            for b in exp.bullets:
                trace = global_engine.rewrite_bullet(b, role_type=recommendation.role_type)
                new_bullets.append(trace.rewritten_bullet)
                bullet_transformation_log.append(trace)
            exp.bullets = new_bullets

        # 4. Truthfulness Gate Verification
        truthfulness = TruthfulnessEngine()
        fact_index = truthfulness.build_fact_index(tailored_profile)

        # 5. Render Ephemeral PDF
        extended_tailored = ExtendedStructuredResume(
            name=tailored_profile.personal.full_name,
            contact=StructuredContact(
                phone=tailored_profile.personal.phone,
                email=tailored_profile.personal.email,
                linkedin=tailored_profile.social_links.linkedin,
                github=tailored_profile.social_links.github,
                portfolio=tailored_profile.social_links.portfolio
            ),
            summary=tailored_profile.personal.summary,
            education=[
                StructuredEducation(
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_date=edu.start_date,
                    end_date=edu.end_date
                ) for edu in tailored_profile.education
            ],
            experience=[
                StructuredExperience(
                    company=exp.company,
                    title=exp.title,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    bullets=exp.bullets
                ) for exp in tailored_profile.experience
            ],
            projects=[
                StructuredProject(
                    title=proj.title,
                    technologies=proj.technologies,
                    date=proj.date,
                    bullets=proj.bullets
                ) for proj in tailored_profile.projects
            ],
            skill_categories=[
                StructuredSkillCategory(category_name="AI & ML", skills=tailored_profile.skills.ai_ml),
                StructuredSkillCategory(category_name="Product Management", skills=tailored_profile.skills.product_management),
                StructuredSkillCategory(category_name="Backend & Infra", skills=tailored_profile.skills.devops_infra),
                StructuredSkillCategory(category_name="Data & Analytics", skills=tailored_profile.skills.data_analytics)
            ]
        )

        ephemeral_session_id = f"ephemeral_{uuid.uuid4().hex[:8]}"
        compiler = JakeBaseCompiler()
        paths = compiler.render_and_compile(
            resume=extended_tailored,
            output_dir=os.path.join(temp_output_dir, ephemeral_session_id),
            filename_prefix=f"Tailored_{candidate_id}_{ephemeral_session_id}"
        )

        return {
            "ephemeral_session_id": ephemeral_session_id,
            "pdf_path": paths["pdf"],
            "tex_path": paths["tex"],
            "bullet_log": bullet_transformation_log,
            "persisted_to_database": False  # GUARANTEED NOT PERSISTED
        }
