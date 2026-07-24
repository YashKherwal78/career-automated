import re
from datetime import datetime
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, ExperienceComparison
from src.discovery.jie.models import StructuredJob

class ExperienceComparer(ComparerInterface):
    @staticmethod
    def _parse_year(date_str: str) -> float:
        if not date_str or date_str.lower().strip() == "present":
            return datetime.now().year + (datetime.now().month / 12.0)
            
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        match = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})\b', date_str, re.IGNORECASE)
        if match:
            m = month_map.get(match.group(1).lower()[:3], 1)
            y = int(match.group(2))
            return y + (m / 12.0)
            
        match_y = re.search(r'\b(\d{4})\b', date_str)
        if match_y:
            return float(match_y.group(1))
            
        return datetime.now().year

    @classmethod
    def calculate_candidate_years(cls, profile: CandidateProfile) -> float:
        total_years = 0.0
        for exp in profile.experience:
            start = cls._parse_year(exp.start_date)
            end = cls._parse_year(exp.end_date)
            duration = max(0.0, end - start)
            total_years += duration
            
        return round(total_years, 1)

    @classmethod
    def compare(cls, profile: CandidateProfile, job: StructuredJob) -> ExperienceComparison:
        """Compares candidate years of experience vs job requirements returning a strongly-typed ExperienceComparison."""
        candidate_years = cls.calculate_candidate_years(profile)
        required_min = job.experience_min or 0
        
        experience_gap = max(0.0, required_min - candidate_years)
        experience_fit = experience_gap == 0.0
        
        score = 1.0 if experience_fit else max(0.0, 1.0 - (experience_gap / 10.0))
        
        # Analyze domains and seniority (e.g. checks role keywords in candidate experience list)
        matched_domains = []
        leadership_match = False
        seniority_match = False
        
        for exp in profile.experience:
            role_lower = exp.role.lower()
            if "lead" in role_lower or "manager" in role_lower or "director" in role_lower:
                leadership_match = True
            if "senior" in role_lower or "sr" in role_lower:
                seniority_match = True
            
        reasoning = [
            f"Candidate has {candidate_years} years of experience vs required {required_min} years.",
            f"Leadership flag matched: {leadership_match}.",
            f"Seniority flag matched: {seniority_match}."
        ]
        
        return ExperienceComparison(
            score=score,
            required_years=required_min,
            candidate_years=candidate_years,
            gap=experience_gap,
            required_domains=[],
            matched_domains=matched_domains,
            leadership_match=leadership_match,
            seniority_match=seniority_match,
            ownership_match=False,
            reasoning=reasoning,
            confidence=0.9
        )
