from typing import Dict, Any
from src.career_intelligence.matching.strategies.base import WeightStrategy
from src.career_intelligence.matching.strategies.implementations import (
    DefaultWeightStrategy, InternshipStrategy, SeniorBackendStrategy, ResearchStrategy, ProductStrategy
)
from src.discovery.jie.models import StructuredJob

class MatchingConfig:
    def __init__(self, strategy: WeightStrategy = None):
        self.strategy = strategy or DefaultWeightStrategy()

    @classmethod
    def auto_detect_strategy(cls, job: StructuredJob) -> "MatchingConfig":
        """Auto-detects the optimal weighting strategy based on job title keywords."""
        title_lower = job.title.lower()
        if "intern" in title_lower:
            return cls(InternshipStrategy())
        elif "senior" in title_lower or "lead" in title_lower or "principal" in title_lower:
            return cls(SeniorBackendStrategy())
        elif "research" in title_lower or "scientist" in title_lower or "phd" in title_lower:
            return cls(ResearchStrategy())
        elif "product" in title_lower or "pm" in title_lower or "program" in title_lower:
            return cls(ProductStrategy())
        return cls(DefaultWeightStrategy())

    def get_weights(self) -> Dict[str, float]:
        """Returns the dictionary weights config for the active strategy."""
        return self.strategy.get_weights()

    def get_weight(self, category: str) -> float:
        """Returns weight for a specified scoring category."""
        return self.strategy.get_weights().get(category, 0.0)
