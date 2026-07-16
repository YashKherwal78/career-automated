import time
from src.runtime.redis.redis_client import RedisClient

class LockManager:
    @classmethod
    def acquire_lock(cls, lock_name: str, acquire_timeout: float = 10.0, lock_timeout: float = 60.0) -> bool:
        """
        Acquires a distributed lock using Redis.
        Returns True if acquired, False otherwise.
        """
        client = RedisClient.get_client()
        lock_key = f"lock:{lock_name}"
        end = time.time() + acquire_timeout
        
        while time.time() < end:
            # nx=True sets key only if it does not exist
            # ex=lock_timeout sets expiration time
            if client.set(lock_key, "locked", ex=int(lock_timeout), nx=True):
                return True
            time.sleep(0.1)
            
        return False

    @classmethod
    def release_lock(cls, lock_name: str):
        """Releases a distributed lock."""
        client = RedisClient.get_client()
        lock_key = f"lock:{lock_name}"
        client.delete(lock_key)
