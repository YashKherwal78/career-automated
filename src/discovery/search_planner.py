from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class SearchTask:
    connector: str
    role_family: str
    canonical_query: str
    locations: List[str]
    experience_profile: List[str]
    employment_types: List[str]
    work_modes: List[str]
    freshness_days: int  # 1, 3, 7
    budget: Dict[str, int] # e.g., {"max_queries": 1, "max_results": 50}

class SearchPlanner:
    """
    Platform-Agnostic Search Planner.
    Generates pure Market Discovery intents based on search profiles.
    Never searches by company.
    """

    @staticmethod
    def generate_market_tasks(profiles: List[Dict[str, Any]], freshness_days: int = 1) -> List[SearchTask]:
        """
        Generates canonical Market Searches.
        """
        tasks = []
        for profile in profiles:
            tasks.append(SearchTask(
                connector="all",
                role_family=profile.get("name", "Unknown"),
                canonical_query=profile.get("keywords", [""])[0],
                locations=profile.get("locations", ["India"]),
                experience_profile=profile.get("experience_profile", ["Entry", "Associate"]),
                employment_types=profile.get("employment_types", ["Full-time"]),
                work_modes=profile.get("work_modes", ["Remote", "Hybrid", "On-site"]),
                freshness_days=freshness_days,
                budget={
                    "max_queries": profile.get("daily_queries", 1),
                    "max_results": profile.get("daily_budget", 50)
                }
            ))
        return tasks
