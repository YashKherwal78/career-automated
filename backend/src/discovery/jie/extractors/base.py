from typing import Any

class BaseExtractor:
    def extract(self, text: str, **kwargs) -> Any:
        """Extracts information from the job description text."""
        raise NotImplementedError("Subclasses must implement extract()")
