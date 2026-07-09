from src.system.logger import setup_logger
logger = setup_logger('discovery_cache')
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.discovery.backends.base_backend import BaseBackend
from src.discovery.backends.backend_factory import BackendFactory

class DiscoveryCache:
    """
    Sits above the backend layer. Checks composite keys before hitting the network.
    """
    def __init__(self):
        self.backend = BackendFactory.get_backend()
        self._memory_cache = {} # In production this would be Redis or SQLite

    def fetch(self, provider_name: str, query: str, location: str, ttl_minutes: int = 60, **kwargs) -> Dict[str, Any]:
        cache_key = f"{provider_name}_{query}_{location}_{datetime.utcnow().strftime('%Y-%m-%d')}"
        
        # Check cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if datetime.utcnow() < entry['expires_at']:
                logger.info(f"DiscoveryCache: Cache HIT for {cache_key}")
                return entry['data']
                
        # Cache miss, fetch from backend
        logger.info(f"DiscoveryCache: Cache MISS for {cache_key}. Hitting network via {self.backend.__class__.__name__}...")
        data = self.backend.fetch(query, location, **kwargs)
        
        # Store in cache
        self._memory_cache[cache_key] = {
            'data': data,
            'expires_at': datetime.utcnow() + timedelta(minutes=ttl_minutes)
        }
        
        return data
