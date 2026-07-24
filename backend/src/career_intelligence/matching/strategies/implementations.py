from typing import Dict
from src.career_intelligence.matching.strategies.base import WeightStrategy

class DefaultWeightStrategy(WeightStrategy):
    def get_weights(self) -> Dict[str, float]:
        return {
            "skills": 0.20,
            "technologies": 0.25,
            "experience": 0.20,
            "projects": 0.10,
            "education": 0.10,
            "location": 0.08,
            "employment": 0.04,
            "certifications": 0.03
        }

class InternshipStrategy(WeightStrategy):
    def get_weights(self) -> Dict[str, float]:
        # Internships prioritize projects and academic education
        return {
            "skills": 0.15,
            "technologies": 0.15,
            "experience": 0.05,
            "projects": 0.40,
            "education": 0.20,
            "location": 0.03,
            "employment": 0.01,
            "certifications": 0.01
        }

class SeniorBackendStrategy(WeightStrategy):
    def get_weights(self) -> Dict[str, float]:
        # Senior engineers require substantial technology depth and leadership experience duration
        return {
            "skills": 0.15,
            "technologies": 0.35,
            "experience": 0.35,
            "projects": 0.05,
            "education": 0.05,
            "location": 0.03,
            "employment": 0.01,
            "certifications": 0.01
        }

class ResearchStrategy(WeightStrategy):
    def get_weights(self) -> Dict[str, float]:
        # Research roles prioritize high education credentials and technical skills
        return {
            "skills": 0.25,
            "technologies": 0.15,
            "experience": 0.15,
            "projects": 0.05,
            "education": 0.35,
            "location": 0.03,
            "employment": 0.01,
            "certifications": 0.01
        }

class ProductStrategy(WeightStrategy):
    def get_weights(self) -> Dict[str, float]:
        # Product managers require soft skills, domain expertise, and responsibilities ownership
        return {
            "skills": 0.35,
            "technologies": 0.05,
            "experience": 0.25,
            "projects": 0.15,
            "education": 0.10,
            "location": 0.06,
            "employment": 0.02,
            "certifications": 0.02
        }
