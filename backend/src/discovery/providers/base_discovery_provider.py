from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List

@dataclass
class OpportunitySeed:
    source: str         # e.g., "duckduckgo", "google"
    ats: str            # e.g., "greenhouse", "lever"
    company_name: str   
    job_url: str        
    job_title: str      
    discovered_query: str
    confidence: float   # 0.0 to 1.0
    strategy_id: str

class BaseDiscoveryProvider(ABC):
    """
    Interface for all discovery providers. 
    Every provider must return a list of OpportunitySeed objects.
    """
    
    @abstractmethod
    def discover(self) -> List[OpportunitySeed]:
        pass
