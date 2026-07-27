import os
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger("AdaptiveProviderConfig")

@dataclass
class ProviderClassDefaults:
    initial_workers: int
    min_workers: int
    max_workers: int
    initial_rps: float
    min_rps: float
    max_rps: float

PROVIDER_CLASSES = {
    "public_json": ProviderClassDefaults(initial_workers=20, min_workers=5, max_workers=100, initial_rps=20.0, min_rps=2.0, max_rps=50.0),
    "rest_api":    ProviderClassDefaults(initial_workers=10, min_workers=3, max_workers=50,  initial_rps=10.0, min_rps=1.0, max_rps=25.0),
    "enterprise":  ProviderClassDefaults(initial_workers=5,  min_workers=1, max_workers=25,  initial_rps=3.0,  min_rps=0.5, max_rps=10.0),
}

PROVIDER_CLASS_MAPPING = {
    "greenhouse": "public_json",
    "lever": "public_json",
    "ashby": "public_json",
    "join_com": "public_json",
    "bamboohr": "rest_api",
    "workable": "rest_api",
    "smartrecruiters": "rest_api",
    "personio": "rest_api",
    "jazzhr": "rest_api",
    "rippling": "rest_api",
    "breezy": "rest_api",
    "icims": "rest_api",
    "teamtailor": "rest_api",
    "recruitee": "rest_api",
    "workday": "enterprise",
    "taleo": "enterprise",
    "oracle": "enterprise",
    "successfactors": "enterprise",
    "cornerstone": "enterprise",
    "avature": "enterprise",
    "eightfold": "enterprise",
    "darwinbox": "rest_api",
    "freshteam": "public_json",
    "keka": "rest_api",
    "zoho_recruit": "rest_api",
}

@dataclass
class ProviderMetrics:
    provider_id: str
    yield_jobs_per_request: float = 0.0
    yield_jobs_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate_pct: float = 100.0
    change_rate_pct: float = 0.0
    backlog_count: int = 0
    last_crawl_time: float = 0.0
    rate_limit_state: bool = False
    health_state: str = "HEALTHY"  # HEALTHY, DEGRADED, RATE_LIMITED, BACKLOGGED, BROKEN, DISABLED


@dataclass
class ProviderConfig:
    provider_id: str
    provider_class: str
    current_workers: int
    min_workers: int
    max_workers: int
    current_rps: float
    min_rps: float
    max_rps: float
    pause_until: float = 0.0
    health_score: float = 100.0
    metrics: ProviderMetrics = field(default_factory=lambda: ProviderMetrics(provider_id=""))


class AdaptiveProviderManager:
    _instance = None

    def __init__(self):
        self.configs: Dict[str, ProviderConfig] = {}
        self._init_defaults()

    def _init_defaults(self):
        for provider_id, cls_name in PROVIDER_CLASS_MAPPING.items():
            defaults = PROVIDER_CLASSES.get(cls_name, PROVIDER_CLASSES["rest_api"])
            self.configs[provider_id] = ProviderConfig(
                provider_id=provider_id,
                provider_class=cls_name,
                current_workers=defaults.initial_workers,
                min_workers=defaults.min_workers,
                max_workers=defaults.max_workers,
                current_rps=defaults.initial_rps,
                min_rps=defaults.min_rps,
                max_rps=defaults.max_rps,
            )

    def get_config(self, provider_id: str) -> ProviderConfig:
        if provider_id not in self.configs:
            defaults = PROVIDER_CLASSES["rest_api"]
            self.configs[provider_id] = ProviderConfig(
                provider_id=provider_id,
                provider_class="rest_api",
                current_workers=defaults.initial_workers,
                min_workers=defaults.min_workers,
                max_workers=defaults.max_workers,
                current_rps=defaults.initial_rps,
                min_rps=defaults.min_rps,
                max_rps=defaults.max_rps,
            )
        return self.configs[provider_id]

    def update_telemetry(self, provider_id: str, success: bool, latency_ms: float, is_429: bool = False, is_403: bool = False):
        cfg = self.get_config(provider_id)
        now = time.time()

        if is_429:
            cfg.current_workers = max(cfg.min_workers, int(cfg.current_workers * 0.5))
            cfg.current_rps = max(cfg.min_rps, cfg.current_rps * 0.5)
            cfg.health_score = max(0.0, cfg.health_score - 25.0)
            logger.warning(f"AIMD Throttling [{provider_id}]: 429 encountered. Workers halved to {cfg.current_workers}, RPS to {cfg.current_rps:.1f}")
        elif is_403:
            cfg.current_workers = cfg.min_workers
            cfg.pause_until = now + 900.0  # Pause for 15 mins
            cfg.health_score = max(0.0, cfg.health_score - 40.0)
            logger.error(f"Circuit Breaker [{provider_id}]: 403 WAF response. Pausing queue until {cfg.pause_until}")
        elif success:
            cfg.health_score = min(100.0, cfg.health_score + 1.0)
            if cfg.health_score > 90.0 and latency_ms < 2000.0:
                # Additive increase
                cfg.current_workers = min(cfg.max_workers, cfg.current_workers + 1)
                cfg.current_rps = min(cfg.max_rps, cfg.current_rps + 1.0)

adaptive_manager = AdaptiveProviderManager()
