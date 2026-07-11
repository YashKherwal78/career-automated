from abc import ABC, abstractmethod
from typing import Optional
from src.discovery.models import InspectionResult

class SourceInspector(ABC):
    """
    Abstract interface for verifying that a detected URL is a valid,
    functioning job board.
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """e.g., 'greenhouse', 'ashby' - must match the adapter's source_name"""
        pass
        
    @abstractmethod
    async def inspect_board(self, url: str) -> InspectionResult:
        """
        Validates the URL using the provider's native API.
        """
        pass

class DefaultInspector(SourceInspector):
    """
    Fallback validator for ATS providers that don't have a dedicated API validator yet.
    Always returns valid=True, confidence=1.0.
    """
    def __init__(self, source_name: str):
        self._source_name = source_name
        
    @property
    def source_name(self) -> str:
        return self._source_name
        
    async def inspect_board(self, url: str) -> InspectionResult:
        return InspectionResult(
            board_exists=True,
            job_count=0,
            api_verified=False,
            canonical_company="",
            endpoint=url
        )
