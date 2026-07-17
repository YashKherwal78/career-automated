import redis
from src.runtime.config.settings import Settings

class MockRedis:
    def __init__(self):
        self.store = {}
        self.lists = {}
        self.hashes = {}
        self.sets = {}

    def sadd(self, key, value):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(str(value))
        return 1

    def sismember(self, key, value):
        if key not in self.sets:
            return False
        return str(value) in self.sets[key]

    def srem(self, key, value):
        if key in self.sets and str(value) in self.sets[key]:
            self.sets[key].remove(str(value))
            return 1
        return 0

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def exists(self, key):
        return key in self.store or key in self.lists or key in self.hashes

    def delete(self, key):
        self.store.pop(key, None)
        self.lists.pop(key, None)
        self.hashes.pop(key, None)

    def rpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)
        return len(self.lists[key])

    def blpop(self, key, timeout=0):
        # Return first item in list if present, else None
        if key in self.lists and self.lists[key]:
            return (key, self.lists[key].pop(0))
        return None

    def llen(self, key):
        return len(self.lists.get(key, []))

    def hset(self, key, mapping=None):
        if key not in self.hashes:
            self.hashes[key] = {}
        self.hashes[key].update(mapping or {})
        return len(mapping) if mapping else 0

    def hgetall(self, key):
        return self.hashes.get(key, {})

    def keys(self, pattern):
        # Support simple prefix matching for keys
        prefix = pattern.replace("*", "")
        all_keys = list(self.store.keys()) + list(self.lists.keys()) + list(self.hashes.keys())
        return [k for k in all_keys if k.startswith(prefix)]

    def expire(self, key, seconds):
        pass


class RedisClient:
    _instance = None
    _is_mock = False

    @classmethod
    def get_client(cls):
        if cls._instance is None:
            if not Settings.REDIS_URL:
                if Settings.ENABLE_LOCAL_FALLBACKS or Settings.APP_ENV == "development":
                    print("WARNING: REDIS_URL not configured. Falling back to MockRedis in-memory store.", flush=True)
                    cls._instance = MockRedis()
                    cls._is_mock = True
                else:
                    raise ValueError("REDIS_URL must be configured in production mode (or set ENABLE_LOCAL_FALLBACKS=true for dev/test fallback).")
            else:
                pool = redis.ConnectionPool.from_url(
                    Settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=30.0,
                    socket_connect_timeout=5.0
                )
                cls._instance = redis.Redis(connection_pool=pool)
                cls._is_mock = False
            
        return cls._instance
