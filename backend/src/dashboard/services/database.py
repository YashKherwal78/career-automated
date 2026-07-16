import os
import requests
import pandas as pd
import time
from typing import Dict, Any
from src.system.logger import setup_logger

logger = setup_logger('api_client')

MISSION_CONTROL_API_URL = os.environ.get("MISSION_CONTROL_API_URL", "http://localhost:8000/api/v1")

class ApiClient:
    _cache = {}
    _cache_time = {}
    _poll_interval = 5  # seconds

    @classmethod
    def _get(cls, endpoint: str, params: dict = None) -> Any:
        url = f"{MISSION_CONTROL_API_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        cache_key = f"{url}_{str(params)}"
        
        now = time.time()
        if cache_key in cls._cache and (now - cls._cache_time.get(cache_key, 0)) < cls._poll_interval:
            return cls._cache[cache_key]

        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            cls._cache[cache_key] = data
            cls._cache_time[cache_key] = now
            return data
        except Exception as e:
            logger.error(f"API Error fetching {url}: {e}")
            return None

    @classmethod
    def get_dashboard_summary(cls):
        return cls._get("/dashboard")

    @classmethod
    def get_workers(cls):
        return cls._get("/workers")

    @classmethod
    def get_jobs(cls, params=None):
        return cls._get("/jobs", params=params)
        
    @classmethod
    def get_companies(cls, params=None):
        return cls._get("/companies", params=params)

    @classmethod
    def get_health(cls):
        return cls._get("/health")

    @classmethod
    def get_repositories_health(cls):
        return cls._get("/system/repositories")

    @classmethod
    def get_system_version(cls):
        return cls._get("/system/version")

    @classmethod
    def get_tier_distribution(cls):
        return cls._get("/health/tiers")

    @classmethod
    def get_coverage(cls):
        return cls._get("/health/coverage")

# Legacy compatibility wrappers
def fetch_table(table_name: str) -> pd.DataFrame:
    # We should no longer use fetch_table. Returning empty for safety during migration.
    return pd.DataFrame()

def fetch_query(query: str, params=()) -> pd.DataFrame:
    # We should no longer use fetch_query.
    return pd.DataFrame()

def get_latest_heartbeats() -> pd.DataFrame:
    workers = ApiClient.get_workers()
    if not workers:
        return pd.DataFrame()
    return pd.DataFrame(workers.get("workers", []))
