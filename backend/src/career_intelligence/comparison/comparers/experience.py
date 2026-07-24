import re
from datetime import datetime
from typing import Dict, Any
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
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
    def compare(cls, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        candidate_years = cls.calculate_candidate_years(profile)
        required_min = job.experience_min or 0
        
        experience_gap = max(0.0, required_min - candidate_years)
        experience_fit = experience_gap == 0.0
        
        return {
            "experience_required": required_min,
            "experience_candidate": candidate_years,
            "experience_gap": experience_gap,
            "experience_fit": experience_fit
        }
