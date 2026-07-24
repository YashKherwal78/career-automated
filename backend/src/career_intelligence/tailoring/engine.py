from typing import Dict, Any, List
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.matching.engine import MatchScoreEngine

class ResumeTailoringEngine:
    def __init__(self):
        self.matcher = MatchScoreEngine()

    def generate_tailoring_plan(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Generates tailored resume suggestions entirely driven by structured comparison data."""
        match_result = self.matcher.calculate_match(profile, job)
        
        # 1. Keyword Optimizations
        # List technologies in job description that are missing from candidate profile
        missing_techs = []
        for tech in job.technologies:
            has_tech = False
            # Check candidate skills
            for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools"]:
                if tech.lower() in [t.lower() for t in getattr(profile.skills, cat, [])]:
                    has_tech = True
                    break
            if not has_tech:
                missing_techs.append(tech)

        # 2. Project Prioritization
        # Rank candidate projects based on technology overlaps with the target job
        project_ranks = []
        job_tech_set = {t.lower() for t in job.technologies}
        
        for idx, proj in enumerate(profile.projects):
            proj_techs = {t.lower() for t in proj.technologies}
            overlap = proj_techs.intersection(job_tech_set)
            project_ranks.append({
                "index": idx,
                "name": proj.name,
                "score": len(overlap),
                "overlap_technologies": list(overlap)
            })
            
        # Sort projects descending by score
        project_ranks.sort(key=lambda x: x["score"], reverse=True)

        return {
            "overall_match_score": match_result["overall_score"],
            "keyword_optimizations": [
                {
                    "type": "technology",
                    "suggestion": f"Incorporate '{tech}' into your summary or skills section.",
                    "canonical_value": tech
                } for tech in missing_techs
            ],
            "project_prioritization": {
                "ordered_project_indices": [p["index"] for p in project_ranks],
                "suggestions": [
                    f"Move '{p['name']}' to the top of your projects section because it highlights relevant stack components ({', '.join(p['overlap_technologies'][:3])})."
                    for p in project_ranks if p["score"] > 0
                ]
            },
            "experience_alignment": {
                "bullet_improvements": [
                    "Tailor experience descriptions to lead with achievements that highlight technology matches."
                ]
            }
        }
