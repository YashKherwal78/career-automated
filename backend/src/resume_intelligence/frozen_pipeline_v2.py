"""
Frozen Architecture V2 End-to-End Pipeline & Storage Contract.

Enforces:
1. Base Resume persisted strictly as JSON (BaseResumeJSONContract) + TeX + PDF artifacts.
2. Exact section semantics preserved (e.g. LIVE_FREELANCE_PRODUCTS).
3. Bullet provenance and ownership level tracking.
4. Ephemeral Tailored Resume generated on demand from stored JSON + JD (NEVER persisted).
"""

import os
import json
from typing import Dict, Any, Optional, List
from src.resume_intelligence.canonical.base_resume_contract import (
    BaseResumeJSONContract, SemanticSection, SemanticSectionType, StructuredSectionItem, BulletProvenance, OwnershipLevel
)
from src.resume_intelligence.tailoring.ownership_engine import OwnershipAwareRuleEngine
from src.resume_intelligence.compiler.jake_resume.extended_models import (
    ExtendedStructuredResume, StructuredContact, StructuredEducation, StructuredExperience, StructuredProject, StructuredSkillCategory, CustomSection, CustomSectionItem
)
from src.resume_intelligence.compiler.jake_base_compiler import JakeBaseCompiler


class BaseResumeRepository:
    """JSON-First Persistent Repository for Base Resumes."""

    def __init__(self, base_storage_dir: str = "artifacts/stored_base_resumes_json"):
        self.storage_dir = base_storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_base_resume_json(self, contract: BaseResumeJSONContract) -> str:
        cand_dir = os.path.join(self.storage_dir, contract.candidate_id)
        os.makedirs(cand_dir, exist_ok=True)
        json_path = os.path.join(cand_dir, "base_resume.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(contract.model_dump(), f, indent=2)
        return json_path

    def load_base_resume_json(self, candidate_id: str) -> Optional[BaseResumeJSONContract]:
        json_path = os.path.join(self.storage_dir, candidate_id, "base_resume.json")
        if not os.path.exists(json_path):
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BaseResumeJSONContract(**data)


class FrozenPipelineV2:
    """Frozen Architecture V2 End-to-End Production Pipeline."""

    def __init__(self):
        self.repo = BaseResumeRepository()
        self.rule_engine = OwnershipAwareRuleEngine()
        self.compiler = JakeBaseCompiler()

    # --------------------------------------------------------------------------
    # STAGE 1: GENERATE & PERSIST BASE RESUME JSON (Source of Truth)
    # --------------------------------------------------------------------------
    def generate_and_persist_base_resume(self, contract: BaseResumeJSONContract) -> Dict[str, str]:
        """Persists candidate's canonical Base Resume as JSON + renders base TeX/PDF artifacts."""
        
        # 1. Save JSON Source of Truth
        json_path = self.repo.save_base_resume_json(contract)

        # 2. Render Base PDF Artifact for Candidate Dashboard
        extended_resume = self._contract_to_extended_resume(contract)
        cand_dir = os.path.join(self.repo.storage_dir, contract.candidate_id)
        
        paths = self.compiler.render_and_compile(
            resume=extended_resume,
            output_dir=cand_dir,
            filename_prefix=f"Canonical_Base_{contract.candidate_id}"
        )

        return {
            "json_source_of_truth": json_path,
            "pdf_artifact": paths["pdf"],
            "tex_artifact": paths["tex"]
        }

    # --------------------------------------------------------------------------
    # STAGE 2: GENERATE EPHEMERAL TAILORED RESUME (Never Persisted)
    # --------------------------------------------------------------------------
    def generate_ephemeral_tailored_resume(
        self,
        candidate_id: str,
        target_jd: str,
        ephemeral_output_dir: str = "artifacts/ephemeral_tailored_outputs"
    ) -> Dict[str, Any]:
        """Loads stored Base Resume JSON, rewrites bullets using resume_knowledge 2 ownership rules, renders PDF. NEVER PERSISTED."""

        base_contract = self.repo.load_base_resume_json(candidate_id)
        assert base_contract is not None, f"Candidate {candidate_id} Base Resume JSON not found!"

        # Deep copy contract for ephemeral transformation
        tailored_contract = base_contract.model_copy(deep=True)
        transformation_logs = []

        for sec in tailored_contract.sections:
            for item in sec.items:
                for prov in item.provenance_bullets:
                    rewritten_prov = self.rule_engine.rewrite_bullet(prov)
                    transformation_logs.append(rewritten_prov)

        # Render Ephemeral Presentation Model
        extended_tailored = self._contract_to_extended_resume(tailored_contract)
        session_dir = os.path.join(ephemeral_output_dir, f"tailored_{candidate_id}")
        
        paths = self.compiler.render_and_compile(
            resume=extended_tailored,
            output_dir=session_dir,
            filename_prefix=f"Tailored_{candidate_id}"
        )

        return {
            "pdf_path": paths["pdf"],
            "tex_path": paths["tex"],
            "bullet_provenance_logs": transformation_logs,
            "is_persisted": False  # GUARANTEED EPHEMERAL
        }

    # --------------------------------------------------------------------------
    # STAGE 2b: TAILORING ENGINE V1 (Strict Guardrails — Never Persisted)
    # --------------------------------------------------------------------------
    def generate_ephemeral_tailored_resume_v1(
        self,
        candidate_id: str,
        job_id: str,
        jd_profile: dict,
        candidate_memory: dict = None,
        kb_path: str = "resume_knowledge",
        confidence_threshold: float = 0.70,
        ephemeral_output_dir: str = "artifacts/ephemeral_tailored_outputs",
    ) -> dict:
        """
        Loads stored Base Resume .tex, runs TailoringEngineV1 with strict guardrails.

        Key differences from generate_ephemeral_tailored_resume():
          - Uses pre-parsed jd_profile (StructuredJobProfile dict) — never re-parses JD
          - Operates directly on .tex string (not CanonicalCandidateProfile model)
          - 3 LLM calls max (summary + experience + projects), not one per bullet
          - IntegrityGate + PolicyGate enforced before any patch is written
          - Returns TailoringResult, not raw PDF paths

        NEVER PERSISTED. is_persisted is always False.
        """
        import os
        from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
        from src.resume_intelligence.tailoring.models_v1 import TailoringInput, HardBlockError

        # Load base .tex from repository
        tex_path = os.path.join(self.repo.storage_dir, candidate_id, "base_resume.tex")
        if not os.path.exists(tex_path):
            raise FileNotFoundError(
                f"Base resume .tex not found for candidate '{candidate_id}' at {tex_path}"
            )
        with open(tex_path, "r", encoding="utf-8") as f:
            base_tex = f.read()

        inp = TailoringInput(
            base_tex=base_tex,
            candidate_memory=candidate_memory or {},
            jd_profile=jd_profile,
            resume_knowledge2_path=kb_path,
            confidence_threshold=confidence_threshold,
            job_id=job_id,
        )

        engine = TailoringEngineV1()
        result = engine.tailor(inp)

        # Optionally write ephemeral .tex to disk (never DB)
        if not result.is_noop:
            import uuid
            session_id = f"tailored_{candidate_id}_{uuid.uuid4().hex[:8]}"
            out_dir = os.path.join(ephemeral_output_dir, session_id)
            os.makedirs(out_dir, exist_ok=True)
            out_tex = os.path.join(out_dir, f"{session_id}.tex")
            with open(out_tex, "w", encoding="utf-8") as f:
                f.write(result.tailored_tex)
            result_dict = result.model_dump()
            result_dict["ephemeral_tex_path"] = out_tex
            result_dict["is_persisted"] = False
            return result_dict

        return {**result.model_dump(), "is_persisted": False}

    def _contract_to_extended_resume(self, contract: BaseResumeJSONContract) -> ExtendedStructuredResume:
        """Adapts BaseResumeJSONContract into ExtendedStructuredResume for Jake compiler."""

        education_items = []
        experience_items = []
        project_items = []
        custom_sections = []

        for sec in contract.sections:
            if sec.section_type == SemanticSectionType.EDUCATION:
                for item in sec.items:
                    education_items.append(
                        StructuredEducation(
                            institution=item.title,
                            degree=item.subtitle if item.subtitle else "",
                            field_of_study="",
                            start_date=item.date if item.date else "",
                            end_date=""
                        )
                    )
            elif sec.section_type == SemanticSectionType.EXPERIENCE:
                for item in sec.items:
                    experience_items.append(
                        StructuredExperience(
                            company=item.title,
                            title=item.subtitle if item.subtitle else "",
                            start_date=item.date if item.date else "",
                            end_date="",
                            bullets=[b.rewritten_text or b.original_text for b in item.provenance_bullets],
                            technologies=item.technologies
                        )
                    )
            elif sec.section_type == SemanticSectionType.PROJECTS:
                for item in sec.items:
                    project_items.append(
                        StructuredProject(
                            title=item.title,
                            technologies=item.technologies,
                            date=item.date if item.date else "",
                            bullets=[b.rewritten_text or b.original_text for b in item.provenance_bullets]
                        )
                    )
            else:
                # Custom semantics (e.g. LIVE_FREELANCE_PRODUCTS)
                c_items = []
                for item in sec.items:
                    c_items.append(
                        CustomSectionItem(
                            title=item.title,
                            technologies=item.technologies,
                            date=item.date,
                            bullets=[b.rewritten_text or b.original_text for b in item.provenance_bullets]
                        )
                    )
                custom_sections.append(CustomSection(section_title=sec.display_title, items=c_items))

        return ExtendedStructuredResume(
            name=contract.name,
            contact=StructuredContact(
                phone=contract.phone,
                email=contract.email,
                linkedin=contract.linkedin,
                github=contract.github,
                portfolio=contract.portfolio
            ),
            summary=contract.summary,
            education=education_items,
            experience=experience_items,
            projects=project_items,
            skill_categories=[
                StructuredSkillCategory(category_name="Technical Skills", skills=["LangGraph", "Python", "FastAPI", "React", "Postgres"])
            ],
            custom_sections=custom_sections
        )
