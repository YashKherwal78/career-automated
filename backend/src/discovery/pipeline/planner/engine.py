import logging
from src.discovery.pipeline.planner.models import CrawlPlan, CrawlStep, RetryPolicy
from src.discovery.pipeline.planner.context import PlanningContext
from src.discovery.pipeline.planner.rules import TransportRule, ConfidenceRule

logger = logging.getLogger("CrawlPlanner")

class CrawlPlanner:
    def __init__(self):
        self.rules = [
            TransportRule(),
            ConfidenceRule()
        ]

    def generate_plan(self, ctx: PlanningContext) -> CrawlPlan:
        workflow = []
        traces = []
        cost = 0.0
        confidence = 100
        
        for rule in self.rules:
            result = rule.evaluate(ctx)
            if "step" in result:
                workflow.append(result["step"])
            if "cost" in result:
                cost += result["cost"]
            if "confidence" in result:
                confidence = result["confidence"]
            if "trace" in result:
                traces.append(result["trace"])
                
        retry_policy = RetryPolicy(max_retries=3 if ctx.intelligence.health_ratio > 0.5 else 1)
        
        return CrawlPlan(
            planner_confidence=confidence,
            decision_trace=traces,
            workflow=workflow,
            retry_policy=retry_policy,
            expected_cost=cost,
            expected_latency_s=ctx.intelligence.historical_latency
        )
