from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class Policy(Enum):
    LOW_COST = "LOW_COST"
    MAXIMUM_COVERAGE = "MAXIMUM_COVERAGE"
    FAST_REFRESH = "FAST_REFRESH"
    RECOVERY = "RECOVERY"
    TESTING = "TESTING"

@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_interval_s: float = 1.0
    exponential_backoff: bool = True
    circuit_breaker_active: bool = False

@dataclass
class CrawlStep:
    step_type: str
    transport: str
    resource_pool: str
    concurrency: int = 1
    timeout_ms: int = 30000

@dataclass
class CrawlPlan:
    planner_confidence: int
    decision_trace: List[str]
    workflow: List[CrawlStep]
    retry_policy: RetryPolicy
    expected_cost: float = 0.0
    expected_latency_s: float = 0.0
