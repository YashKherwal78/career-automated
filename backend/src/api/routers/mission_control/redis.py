import time
from fastapi import APIRouter
from src.runtime.redis.redis_client import RedisClient
from src.runtime.redis.queue_manager import QueueManager

router = APIRouter()


@router.get("")
def get_redis():
    try:
        client = RedisClient.get_client()
    except ValueError as e:
        return {"status": "unconfigured", "error": str(e)}

    is_mock = getattr(RedisClient, "_is_mock", False)

    start = time.monotonic()
    try:
        if is_mock:
            client.set("__healthcheck__", "1")
            client.get("__healthcheck__")
        else:
            client.ping()
        reachable = True
        error = None
    except Exception as e:
        reachable = False
        error = str(e)
    latency_ms = round((time.monotonic() - start) * 1000, 2)

    queues = []
    if reachable:
        try:
            queue_keys = client.keys("queue:*")
            for key in queue_keys:
                name = key.split("queue:", 1)[-1]
                queues.append({"name": name, "size": QueueManager.size(name)})
        except Exception:
            pass

    return {
        "status": "reachable" if reachable else "unreachable",
        "backend": "mock (in-memory, no REDIS_URL/dev fallback)" if is_mock else "redis",
        "latency_ms": latency_ms if reachable else None,
        "error": error,
        "queues": queues,
    }
