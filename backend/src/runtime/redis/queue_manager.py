import json
from typing import Optional, Any
from src.runtime.redis.redis_client import RedisClient

class QueueManager:
    @classmethod
    def enqueue(cls, queue_name: str, payload: Any):
        """Enqueues an item into a Redis list."""
        client = RedisClient.get_client()
        queue_key = f"queue:{queue_name}"
        client.rpush(queue_key, json.dumps(payload))

    @classmethod
    def dequeue(cls, queue_name: str, timeout: int = 5) -> Optional[Any]:
        """
        Dequeues an item from a Redis list (blocking pop).
        Returns None if queue is empty or times out.
        """
        client = RedisClient.get_client()
        queue_key = f"queue:{queue_name}"
        # blpop returns (key, value) tuple
        result = client.blpop(queue_key, timeout=timeout)
        if result:
            return json.loads(result[1])
        return None

    @classmethod
    def size(cls, queue_name: str) -> int:
        """Returns the size of the queue."""
        client = RedisClient.get_client()
        queue_key = f"queue:{queue_name}"
        return client.llen(queue_key)
