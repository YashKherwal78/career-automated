import os
from typing import Dict
from src.career_intelligence.matching.weights import DEFAULT_MATCH_WEIGHTS

class MatchingConfig:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_MATCH_WEIGHTS

    def get_weight(self, category: str) -> float:
        """Returns weight for a specified scoring category."""
        return self.weights.get(category, 0.0)
