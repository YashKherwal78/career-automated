from abc import ABC, abstractmethod
from typing import Any, Dict, List

class SourceAdapter(ABC):
    """
    Abstract plugin interface for ATS platforms.
    Adding a new ATS provider simply requires registering a new class that implements this.
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """e.g., 'greenhouse', 'lever'"""
        pass
        
    @property
    @abstractmethod
    def parser_version(self) -> str:
        """e.g., 'v1.0' - Used to determine if jobs need re-parsing."""
        pass
        
    @abstractmethod
    def detect(self, url: str) -> bool:
        """Returns True if this adapter can handle the given URL."""
        pass
        
    @abstractmethod
    async def fetch(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs the network I/O. 
        Takes a task (like a company endpoint) and returns raw JSON/HTML payload.
        Should handle pagination and backoff internally if needed.
        """
        pass
        
    @abstractmethod
    def parse(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the raw payload into a structured format without network calls.
        """
        pass
        
    @abstractmethod
    def discover_jobs(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts individual job postings from the parsed data.
        """
        pass
        
    @abstractmethod
    def discover_companies(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts newly discovered companies (e.g. from an aggregator payload).
        """
        pass
