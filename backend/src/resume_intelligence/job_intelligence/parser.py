"""
Job Description Intelligence Parser & Taxonomy Normalizer.

Parses raw JD text into a canonical StructuredJobProfile using deterministic regex/ontology rules
and resume_knowledge 2 skill maps. 0 fabrication, strictly grounded in the JD text.
"""

import re
import time
import hashlib
from typing import List, Dict, Any, Set
from src.resume_intelligence.job_intelligence.models import (
    StructuredJobProfile, ExtractedSkillItem, ATSKeywordItem, ResumeStrategySignals, RequirementType
)


class JobDescriptionParser:
    """Parses raw Job Description text into structured intelligence without hallucination."""

    TECH_ALIASES = {
        "postgres": "postgresql",
        "postgre": "postgresql",
        "react.js": "react",
        "reactjs": "react",
        "vue.js": "vue",
        "vuejs": "vue",
        "node.js": "nodejs",
        "node": "nodejs",
        "aws": "amazon web services",
        "gcp": "google cloud platform",
        "k8s": "kubernetes",
        "fast api": "fastapi",
        "py": "python"
    }

    KNOWN_SKILLS = {
        "python": ("programming_language", ["python", "py"]),
        "fastapi": ("framework", ["fastapi", "fast api"]),
        "react": ("framework", ["react", "react.js", "reactjs"]),
        "postgresql": ("database", ["postgres", "postgresql", "postgre"]),
        "redis": ("database", ["redis"]),
        "docker": ("devops_tools", ["docker"]),
        "kubernetes": ("devops_tools", ["kubernetes", "k8s"]),
        "langgraph": ("ai_frameworks", ["langgraph"]),
        "langchain": ("ai_frameworks", ["langchain"]),
        "llm": ("ai_frameworks", ["llm", "large language model", "llms"]),
        "rag": ("ai_frameworks", ["rag", "retrieval-augmented generation"]),
        "roadmapping": ("product_frameworks", ["roadmap", "roadmapping"]),
        "customer discovery": ("product_frameworks", ["customer discovery", "user research"]),
        "figma": ("design_tools", ["figma"])
    }

    def parse_job_description(
        self,
        job_id: str,
        company_name: str,
        role_title: str,
        raw_description: str
    ) -> StructuredJobProfile:
        """Parses JD text into a canonical StructuredJobProfile strictly grounded in raw_description."""

        jd_lower = raw_description.lower()
        job_hash = hashlib.sha256(f"{company_name}_{role_title}_{jd_lower}".encode("utf-8")).hexdigest()

        # 1. Normalize & Extract Technologies & Skills
        required_skills: List[ExtractedSkillItem] = []
        technologies_set: Set[str] = set()
        ats_keywords: List[ATSKeywordItem] = []

        for skill_norm, (cat, aliases) in self.KNOWN_SKILLS.items():
            freq = sum(len(re.findall(r'\b' + re.escape(alias) + r'\b', jd_lower)) for alias in aliases)
            if freq > 0:
                technologies_set.add(skill_norm)
                req_type = RequirementType.PREFERRED if ("preferred" in jd_lower and skill_norm in jd_lower.split("preferred")[1]) else RequirementType.REQUIRED
                
                required_skills.append(
                    ExtractedSkillItem(
                        name=skill_norm.capitalize(),
                        normalized_name=skill_norm,
                        category=cat,
                        requirement_type=req_type,
                        importance_score=min(1.0, 0.4 + (freq * 0.2)),
                        frequency=freq
                    )
                )
                ats_keywords.append(
                    ATSKeywordItem(
                        keyword=skill_norm.capitalize(),
                        normalized_keyword=skill_norm,
                        weight=min(1.0, 0.5 + (freq * 0.25)),
                        category=cat
                    )
                )

        # 2. Extract Responsibilities
        responsibilities = []
        for line in raw_description.split("\n"):
            clean_l = line.strip(" •-*")
            if len(clean_l) > 20 and any(w in clean_l.lower() for w in ["build", "lead", "design", "develop", "manage", "drive", "deliver"]):
                responsibilities.append(clean_l)

        # 3. Infer Role Type & Resume Strategy Signals
        role_type = "SDE"
        if any(k in role_title.lower() or k in jd_lower for k in ["ai", "llm", "langgraph", "machine learning"]):
            role_type = "AI Engineer"
        elif any(k in role_title.lower() or k in jd_lower for k in ["product manager", "pm", "roadmap", "discovery"]):
            role_type = "Product Manager"
        elif "backend" in role_title.lower() or "backend" in jd_lower:
            role_type = "Backend"

        # Domain Inference
        domain = "SaaS"
        if "fintech" in jd_lower or "credit" in jd_lower:
            domain = "FinTech"
        elif "ai" in jd_lower or "agent" in jd_lower:
            domain = "AI"

        strategy_signals = ResumeStrategySignals(
            role_type=role_type,
            primary_domain=domain,
            summary_strategy=f"Calibrate narrative towards {role_type} in {domain} domain.",
            bullet_strategy="Emphasize system architecture, quantitative metric impact, and technical ownership.",
            preferred_ownership_style="LEAD" if "lead" in role_title.lower() else "OWNER",
            priority_keywords=[k.keyword for k in ats_keywords[:5]],
            priority_project_types=[role_type, domain]
        )

        return StructuredJobProfile(
            job_id=job_id,
            job_hash=job_hash,
            company_name=company_name,
            role_title=role_title,
            required_skills=required_skills,
            ats_keywords=ats_keywords,
            responsibilities=responsibilities[:8],
            technologies=sorted(list(technologies_set)),
            business_domains=[domain],
            strategy_signals=strategy_signals,
            parsed_at=time.time()
        )
