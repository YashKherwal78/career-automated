from abc import ABC, abstractmethod
from typing import List, Dict

class JobProvider(ABC):
    """Abstract base class for all job providers."""
    
    @abstractmethod
    def discover_jobs(self) -> List[Dict]:
        """
        Discover jobs and return a list of job dictionaries.
        Expected keys:
        - company_name (str)
        - job_title (str)
        - job_url (str)
        - job_description (str)
        - location (str)
        - experience_required (str)
        - skills_required (str)
        - employment_type (str)
        - posting_date (str)
        - days_old (int)
        """
        pass
