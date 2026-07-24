from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, ResponsibilityComparison
from src.discovery.jie.models import StructuredJob

class ResponsibilityComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> ResponsibilityComparison:
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
                
        total = len(matched) + len(missing)
        score = len(matched) / total if total > 0 else 1.0
        reasoning = [
            f"Candidate matches {len(matched)} out of {total} job responsibilities."
        ]

        return ResponsibilityComparison(
            score=score,
            matched=matched,
            missing=missing,
            reasoning=reasoning,
            confidence=0.8
        )
