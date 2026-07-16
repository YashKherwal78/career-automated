import time
from typing import Dict, List
from src.runtime.redis.redis_client import RedisClient

class HeartbeatManager:
    @classmethod
    def register_worker(cls, worker_id: str, metadata: dict = None):
        """Registers or updates a worker with a heartbeat TTL."""
        client = RedisClient.get_client()
        worker_key = f"worker:active:{worker_id}"
        hb_data = {
            "worker_id": worker_id,
            "last_seen": time.time(),
            "metadata": metadata or {}
        }
        client.hset(worker_key, mapping={
            "last_seen": hb_data["last_seen"],
            "metadata": str(hb_data["metadata"])
        })
        # Heartbeat expiration: automatically expires in 30 seconds if no heartbeat
        client.expire(worker_key, 30)

    @classmethod
    def get_active_workers(cls) -> List[dict]:
        """Retrieves list of active registered workers."""
        client = RedisClient.get_client()
        workers = []
        keys = client.keys("worker:active:*")
        for key in keys:
            data = client.hgetall(key)
            if data:
                workers.append({
                    "worker_id": key.split("worker:active:")[1],
                    "last_seen": float(data.get("last_seen", 0)),
                    "metadata": eval(data.get("metadata", "{}"))
                })
        return workers
