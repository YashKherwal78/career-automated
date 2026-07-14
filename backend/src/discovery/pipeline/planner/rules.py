from typing import List
from src.discovery.pipeline.planner.context import PlanningContext
from src.discovery.pipeline.planner.models import CrawlStep, RetryPolicy

class ComposableRule:
    def evaluate(self, ctx: PlanningContext) -> dict:
        raise NotImplementedError

class TransportRule(ComposableRule):
    def evaluate(self, ctx: PlanningContext) -> dict:
        cost = 1.0
        transport = "JSON"
        pool = "HTTP_POOL"
        trace = "JSON chosen (health > 90%)"
        
        if ctx.intelligence.health_ratio < 0.5:
            if ctx.current_policy.name == "LOW_COST":
                transport = "HTML"
                pool = "PREMIUM_PROXY"
                cost = 10.0
                trace = "HTML chosen via Proxy (health < 50, Low Cost Policy)"
            else:
                transport = "BROWSER"
                pool = "BROWSER_POOL"
                cost = 100.0
                trace = "Playwright chosen (health < 50, Coverage Policy)"

        return {
            "step": CrawlStep(step_type="FETCH", transport=transport, resource_pool=pool),
            "cost": cost,
            "trace": trace
        }

class ConfidenceRule(ComposableRule):
    def evaluate(self, ctx: PlanningContext) -> dict:
        confidence = 100
        if ctx.intelligence.historical_latency > 5.0:
            confidence -= 10
        if ctx.intelligence.schema_hash == "unknown":
            confidence -= 50
        return {"confidence": confidence, "trace": f"Confidence set to {confidence}"}
