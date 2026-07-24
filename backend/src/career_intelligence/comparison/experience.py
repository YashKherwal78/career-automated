import re
from datetime import datetime
from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class ExperienceComparer:
    @staticmethod
    def _parse_year(date_str: str) -> float:
        """Helper to parse a date string like 'Feb 2026', '2024' or 'Present' into year values."""
        if not date_str or date_str.lower().strip() == "present":
            return datetime.now().year + (datetime.now().month / 12.0)
            
        # Try to find year and month
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        # Match 'MMM YYYY'
        match = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})\b', date_str, re.IGNORECASE)
        if match:
            m = month_map.get(match.group(1).lower()[:3], 1)
            y = int(match.group(2))
            return y + (m / 12.0)
            
        # Match just 'YYYY'
        match_y = re.search(r'\b(\d{4})\b', date_str)
        if match_y:
            return float(match_y.group(1))
            
        return datetime.now().year

    @classmethod
    def calculate_candidate_years(cls, profile: CandidateProfile) -> float:
        """Calculates total candidate years of experience from experience listings."""
        total_years = 0.0
        for exp in profile.experience:
            start = cls._parse_year(exp.start_date)
            end = cls._parse_year(exp.end_date)
            duration = max(0.0, end - start)
            total_years += duration
            
        return round(total_years, 1)

    @classmethod
    def compare(cls, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares required minimum/maximum years of experience vs candidate profile."""
        candidate_years = cls.calculate_candidate_years(profile)
        
        # Default match if no minimum required
        if job.experience_min is None:
            return {
                "score": 1.0,
                "fit": True,
                "candidate_years": candidate_years,
                "required_min": None,
                "reason": "No minimum experience requirement specified."
            }

        if candidate_years >= job.experience_min:
            score = 1.0
            fit = True
            reason = f"Candidate experience ({candidate_years} yrs) meets minimum requirement ({job.experience_min} yrs)."
        else:
            # Scale score based on gap, minimum 0.0
            score = max(0.0, candidate_years / job.experience_min)
            fit = False
            reason = f"Candidate has {candidate_years} yrs of experience, but job requires minimum {job.experience_min} yrs."

        return {
            "score": score,
            "fit": fit,
            "candidate_years": candidate_years,
            "required_min": job.experience_min,
            "reason": reason
        }
