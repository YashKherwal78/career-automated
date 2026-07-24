from typing import List, Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.matching.engine import MatchScoreEngine

class JobRecommendationEngine:
    def __init__(self):
        self.scorer = MatchScoreEngine()

    def get_recommendations(self, profile: CandidateProfile, jobs: List[StructuredJob]) -> Dict[str, List[Dict[str, Any]]]:
        """Classifies and recommends jobs based on candidate profile match calculations."""
        scored_jobs = []
        for job in jobs:
            res = self.scorer.calculate_match(profile, job)
            scored_jobs.append({
                "job": job,
                "score": res["overall_score"],
                "breakdown": res["breakdown"],
                "gaps": res["gaps"]
            })

        # Sort jobs by overall match score descending
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)

        best_matching = []
        high_match = []
        stretch_opps = []
        hidden_opps = []

        for item in scored_jobs:
            score = item["score"]
            job = item["job"]
            
            job_dict = {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "score": score
            }

            if score >= 85:
                best_matching.append(job_dict)
            elif score >= 70:
                high_match.append(job_dict)
            elif score >= 50:
                stretch_opps.append(job_dict)
                
            # Hidden Opportunity: high technology overlap but lower overall score (e.g. experience gap is large)
            if item["breakdown"]["technologies"] >= 80 and score < 70:
                hidden_opps.append(job_dict)

        return {
            "best_matching_jobs": best_matching[:10],
            "high_match_jobs": high_match[:10],
            "stretch_opportunities": stretch_opps[:10],
            "hidden_opportunities": hidden_opps[:10]
        }
