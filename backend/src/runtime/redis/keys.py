class RedisKeys:
    # Queues
    DISCOVER_QUEUE = "queue:discover"
    VERIFY_QUEUE = "queue:verify"
    CRAWL_QUEUE = "queue:crawl"
    
    # Locks
    COMPANY_LOCK = "lock:company:{company_id}"
    PROVIDER_LOCK = "lock:provider:{provider}"
    
    # Workers & Heartbeats
    WORKER_INFO = "worker:{worker_id}"
    WORKER_HEARTBEAT = "heartbeat:{worker_id}"
    
    # Sessions
    CRAWL_SESSION = "session:{session_id}"
    
    # Caches & Rate Limits
    JOB_CACHE = "cache:job:{job_hash}"
    RATE_LIMIT = "rate_limit:{provider}"

    @classmethod
    def get_company_lock(cls, company_id: str) -> str:
        return cls.COMPANY_LOCK.format(company_id=company_id)

    @classmethod
    def get_provider_lock(cls, provider: str) -> str:
        return cls.PROVIDER_LOCK.format(provider=provider)

    @classmethod
    def get_worker_info(cls, worker_id: str) -> str:
        return cls.WORKER_INFO.format(worker_id=worker_id)

    @classmethod
    def get_worker_heartbeat(cls, worker_id: str) -> str:
        return cls.WORKER_HEARTBEAT.format(worker_id=worker_id)

    @classmethod
    def get_crawl_session(cls, session_id: str) -> str:
        return cls.CRAWL_SESSION.format(session_id=session_id)

    @classmethod
    def get_job_cache(cls, job_hash: str) -> str:
        return cls.JOB_CACHE.format(job_hash=job_hash)

    @classmethod
    def get_rate_limit(cls, provider: str) -> str:
        return cls.RATE_LIMIT.format(provider=provider)
