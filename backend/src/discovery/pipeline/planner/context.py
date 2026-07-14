from dataclasses import dataclass
from typing import Dict, Any, Optional
from src.discovery.pipeline.planner.models import Policy
from src.discovery.models import ConnectorCapability

@dataclass
class EndpointIntelligence:
    confidence_score: int
    health_ratio: float
    historical_latency: float
    failure_rate: float
    schema_hash: str

@dataclass
class RuntimeState:
    queue_depth: int
    executor_capacity: int
    active_workers: int
    browser_pool_capacity: int

@dataclass
class PlanningContext:
    current_policy: Policy
    capabilities: ConnectorCapability
    intelligence: EndpointIntelligence
    metrics: Dict[str, Any]
    runtime: RuntimeState

class PlanningContextBuilder:
    def __init__(self, ats_registry=None, connector_registry=None):
        self.ats_registry = ats_registry
        self.connector_registry = connector_registry

    def build(self, board_identity: Any, policy: Policy) -> PlanningContext:
        # Mocking the load of capabilities, intelligence, and runtime.
        # In a real environment, this connects to the registries and DB.
        capabilities = ConnectorCapability(
            pagination="offset",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=False,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=False,
            supports_bulk_fetch=True,
            supports_location=False,
            supports_departments=False,
            supports_remote=False
        )
        intelligence = EndpointIntelligence(
            confidence_score=95,
            health_ratio=0.99,
            historical_latency=1.2,
            failure_rate=0.01,
            schema_hash="abc1234"
        )
        runtime = RuntimeState(
            queue_depth=10,
            executor_capacity=50,
            active_workers=10,
            browser_pool_capacity=5
        )
        metrics = {"avg_latency": 1.2}
        return PlanningContext(
            current_policy=policy,
            capabilities=capabilities,
            intelligence=intelligence,
            metrics=metrics,
            runtime=runtime
        )
