from typing import List, Dict, Any
from src.resume.models import StructuredJob, CandidateFit, RewriteStrategy
import re

class RewritePlanner:
    def _score_items(self, items: List[Dict[str, Any]], job: StructuredJob) -> Dict[str, float]:
        scores = {}
        for item in items:
            text = str(item).lower()
            score = 0
            for skill in job.mandatory_skills:
                if skill.lower() in text:
                    score += 2
            for skill in job.preferred_skills:
                if skill.lower() in text:
                    score += 1
            scores[item['id']] = score
        return scores

    def generate_strategy(self, job: StructuredJob, fit: CandidateFit, knowledge: Dict[str, Any]) -> RewriteStrategy:
        # Score projects and internships
        proj_scores = self._score_items(knowledge.get('projects', []), job)
        int_scores = self._score_items(knowledge.get('internships', []), job)
        
        # Sort by score descending
        sorted_projs = sorted(proj_scores.items(), key=lambda x: x[1], reverse=True)
        sorted_ints = sorted(int_scores.items(), key=lambda x: x[1], reverse=True)
        
        prioritized = [p[0] for p in sorted_projs[:2]] + [i[0] for i in sorted_ints[:1]]
        
        return RewriteStrategy(
            priority_skills=job.mandatory_skills[:5],
            priority_responsibilities=job.responsibilities[:3],
            tone="Assertive",
            sections_to_prioritize=prioritized,
            bullet_order={}, # Deterministic ordering based on relevance could go here
            rewrite_style="assertive"
        )
