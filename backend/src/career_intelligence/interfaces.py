from typing import Any

class ComparerInterface:
    def compare(self, profile: Any, job: Any) -> Any:
        """Executes domain comparison logic."""
        raise NotImplementedError("Subclasses must implement compare()")

class ScorerInterface:
    def calculate_score(self, comparison: Any) -> Any:
        """Calculates scoring attributes from comparison data."""
        raise NotImplementedError("Subclasses must implement calculate_score()")

class AnalyzerInterface:
    def analyze_gaps(self, comparison: Any) -> Any:
        """Analyzes gaps from comparison data."""
        raise NotImplementedError("Subclasses must implement analyze_gaps()")
