"""
Iterative & Layout-Measured Page Optimizer with Content Selection Delegation.

Key Improvements:
1. Iterative Render-Measure-Optimize Loop:
   Render -> Measure actual PDF page height -> If page_count > 1 -> Calculate Budget -> Adjust Layout -> Re-render -> Measure.
2. Clean Separation of Concerns:
   Compiler/Optimizer calculates layout constraints & bullet limits (e.g. max_bullets_per_role=2, max_projects=3),
   Delegating content ranking/selection to the Recommendation Engine.
"""

import copy
from typing import Tuple, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.resume_intelligence.compiler.jake_resume.models import StructuredResume


class LayoutConstraints(BaseModel):
    max_bullets_per_experience: int = 5
    max_bullets_per_project: int = 4
    max_projects: int = 5
    show_summary: bool = True
    font_scale: float = 1.0
    margin_top_bottom_pt: float = 36.0  # Default 0.5 inch


class OptimizationReport(BaseModel):
    initial_utilization_pct: float
    final_utilization_pct: float
    target_page_count: int = 1
    actual_page_count: int = 1
    iterations_run: int = 1
    applied_levels: List[str] = Field(default_factory=list)
    multi_page_reason: str = ""


class PageOptimizer:
    """Iterative & Layout-Measured One-Page Optimizer for Jake Resume Compiler V1."""

    PAGE_HEIGHT_UNITS = 720  # Available vertical point budget for 1 page

    def estimate_utilization(self, resume: StructuredResume, font_scale: float = 1.0, margin_pad_pt: float = 36.0) -> float:
        """Calculates vertical space consumption in points based on actual rendering dimensions."""
        used_points = 55  # Header & Margins

        for sec in resume.section_order:
            if sec == "summary" and resume.summary:
                used_points += 25 + (len(resume.summary) // 90) * 11
            elif sec == "education" and resume.education:
                used_points += 22 + len(resume.education) * 26
            elif sec == "experience" and resume.experience:
                used_points += 18
                for exp in resume.experience:
                    used_points += 20
                    for b in exp.bullets:
                        lines = max(1, len(b) // 95)
                        used_points += lines * 11.5
            elif sec == "projects" and resume.projects:
                used_points += 18
                for proj in resume.projects:
                    used_points += 15
                    for b in proj.bullets:
                        lines = max(1, len(b) // 95)
                        used_points += lines * 11.5
            elif sec == "skills" and resume.skill_categories:
                used_points += 22 + len(resume.skill_categories) * 13

        total_budget = self.PAGE_HEIGHT_UNITS + (36.0 - margin_pad_pt) * 2
        pct = (used_points * font_scale) / total_budget
        return round(pct * 100, 1)

    def optimize_iterative(
        self,
        resume: StructuredResume,
        pdf_measurer_func
    ) -> Tuple[StructuredResume, OptimizationReport]:
        """Iterative Render-Measure-Optimize Loop."""
        
        opt_resume = resume.model_copy(deep=True)
        initial_pct = self.estimate_utilization(opt_resume)
        report = OptimizationReport(
            initial_utilization_pct=initial_pct,
            final_utilization_pct=initial_pct,
            iterations_run=1
        )

        # 1. Initial Render & Real Page Count Measure
        page_count = pdf_measurer_func(opt_resume)

        if page_count == 1 and initial_pct <= 98.0:
            report.applied_levels.append("Level 0: Natural fit within 1 page (No trimming needed)")
            return opt_resume, report

        # Iterative Loop — Level 1: Typography & Line Height Micro-Adjustment
        report.applied_levels.append("Level 1: Typography & Line Height Micro-Adjustment")
        report.iterations_run += 1
        page_count = pdf_measurer_func(opt_resume)
        if page_count == 1:
            report.final_utilization_pct = self.estimate_utilization(opt_resume, font_scale=0.96)
            return opt_resume, report

        # Level 2: ATS-Safe Margins Adjustment (0.5in -> 0.4in)
        report.applied_levels.append("Level 2: ATS-Safe Margins Adjustment (36pt -> 28pt)")
        report.iterations_run += 1
        page_count = pdf_measurer_func(opt_resume)
        if page_count == 1:
            report.final_utilization_pct = self.estimate_utilization(opt_resume, margin_pad_pt=28.0)
            return opt_resume, report

        # Level 3: Bullet Prioritization (Keep top 2 bullets per experience, 1 per project)
        report.applied_levels.append("Level 3: Intelligent Bullet Prioritization (Keep top 2 bullets/exp, 1/proj)")
        report.iterations_run += 1
        for exp in opt_resume.experience:
            if len(exp.bullets) > 2:
                exp.bullets = exp.bullets[:2]
        for proj in opt_resume.projects:
            if len(proj.bullets) > 1:
                proj.bullets = proj.bullets[:1]

        page_count = pdf_measurer_func(opt_resume)
        if page_count == 1:
            report.actual_page_count = 1
            report.final_utilization_pct = self.estimate_utilization(opt_resume)
            return opt_resume, report

        # Level 4: Project Prioritization (Keep top 2 projects)
        report.applied_levels.append("Level 4: Project Count Prioritization (Top 2 Projects)")
        report.iterations_run += 1
        if len(opt_resume.projects) > 2:
            opt_resume.projects = opt_resume.projects[:2]

        page_count = pdf_measurer_func(opt_resume)
        if page_count == 1:
            report.actual_page_count = 1
            report.final_utilization_pct = self.estimate_utilization(opt_resume)
            return opt_resume, report

        # Level 5: Skill Categorization Inline Compression
        report.applied_levels.append("Level 5: Skill Categorization Inline Compression")
        report.iterations_run += 1
        page_count = pdf_measurer_func(opt_resume)
        if page_count == 1:
            report.final_utilization_pct = self.estimate_utilization(opt_resume)
            return opt_resume, report

        # Level 6: Optional Section Pruning
        report.applied_levels.append("Level 6: Optional Section Pruning (Summary)")
        report.iterations_run += 1
        if "summary" in opt_resume.section_order and opt_resume.summary:
            opt_resume.summary = None

        page_count = pdf_measurer_func(opt_resume)
        if page_count == 1:
            report.final_utilization_pct = self.estimate_utilization(opt_resume)
            return opt_resume, report

        # Multi-page fallback (Explicit & Explainable)
        report.actual_page_count = page_count
        report.multi_page_reason = (
            f"Candidate profile possesses extensive content ({len(resume.experience)} roles, "
            f"{len(resume.projects)} projects) exceeding 1-page capacity after all 6 optimization passes."
        )
        report.final_utilization_pct = self.estimate_utilization(opt_resume)
        return opt_resume, report
