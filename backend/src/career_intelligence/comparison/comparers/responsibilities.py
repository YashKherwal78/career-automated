from typing import Dict, Any, List
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class ResponsibilityComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, List[str]]:
        """Matches experience bullet points overlap with job responsibilities."""
        cand_bullets = []
        for exp in profile.experience:
            cand_bullets.extend([b.lower() for b in exp.bullet_points])
            
        matched = []
        missing = []
        
        for resp in job.responsibilities:
            resp_words = set(resp.lower().split())
            matched_flag = False
            for bullet in cand_bullets:
                bullet_words = set(bullet.split())
                if len(resp_words.intersection(bullet_words)) >= 3:
                    matched_flag = True
                    break
            if matched_flag:
                matched.append(resp)
            else:
                missing.append(resp)
                
        return {
            "responsibility_matches": matched,
            "responsibility_gaps": missing
        }
