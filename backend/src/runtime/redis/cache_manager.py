from typing import Optional
from src.runtime.redis.redis_client import RedisClient

class CacheManager:
    @classmethod
    def get(cls, key: str) -> Optional[str]:
        """Gets value from cache."""
        client = RedisClient.get_client()
        return client.get(f"cache:{key}")

    @classmethod
    def set(cls, key: str, value: str, ttl: int = 3600):
        """Sets value in cache with a TTL (default 1 hour)."""
        client = RedisClient.get_client()
        client.set(f"cache:{key}", value, ex=ttl)

    @classmethod
    def is_cached(cls, key: str) -> bool:
        """Checks if key is present in cache."""
        client = RedisClient.get_client()
        return bool(client.exists(f"cache:{key}"))

    @classmethod
    def invalidate(cls, key: str):
        """Removes key from cache."""
        client = RedisClient.get_client()
        client.delete(f"cache:{key}")
