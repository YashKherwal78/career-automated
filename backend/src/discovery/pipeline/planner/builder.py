from typing import Any
from src.discovery.pipeline.planner.models import Policy
from src.discovery.pipeline.planner.context import PlanningContext, EndpointIntelligence, RuntimeState
from src.discovery.models import ConnectorCapability

class PlanningContextBuilder:
    def __init__(self, ats_registry=None, connector_registry=None):
        self.ats_registry = ats_registry
        self.connector_registry = connector_registry

    def build(self, board_identity: Any, policy: Policy) -> PlanningContext:
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
