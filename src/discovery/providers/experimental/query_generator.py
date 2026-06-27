import uuid
from typing import List
from src.discovery.providers.base_discovery_provider import OpportunitySeed

class QueryGenerator:
    """
    Passive Data Collection Query Generator.
    Generates permutations of roles, locations, and startup keywords.
    Does NOT suppress queries. Simply yields them so they can be logged.
    """
    
    ROLES = [
        "Product Manager",
        "Associate Product Manager",
        "AI Product Manager",
        "Founder's Office"
    ]
    
    STARTUP_KEYWORDS = [
        "startup",
        "seed",
        "YC"
    ]
    
    LOCATIONS = [
        "Remote",
        "India",
        "Bangalore"
    ]

    def generate_strategies(self, provider_name: str, backend_name: str, ats: str) -> List[dict]:
        """
        Returns a list of strategy dictionaries to be executed.
        """
        strategies = []
        for role in self.ROLES:
            for kw in self.STARTUP_KEYWORDS:
                for loc in self.LOCATIONS:
                    query = f'site:boards.greenhouse.io "{role}" {kw} {loc}'
                    strategy_id = str(uuid.uuid4())
                    
                    strategies.append({
                        "strategy_id": strategy_id,
                        "provider": provider_name,
                        "backend": backend_name,
                        "ats": ats,
                        "query": query,
                        "location": loc,
                        "startup_filter": kw,
                        "rule_version": "1.1.0",
                        "active": 1
                    })
        return strategies
