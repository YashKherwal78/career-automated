"""
Health & Observability API
GET /api/v1/health          - system health check
GET /api/v1/health/pipeline - full pipeline funnel metrics
GET /api/v1/health/connectors - per-ATS connector reliability
GET /api/v1/health/coverage   - top company coverage report
"""
import time
from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.get("")
def health_check(repos = Depends(get_repos)):
    """Basic health probe for Railway / uptime monitors."""
    try:
        return repos.dashboard.get_health_check()
    except Exception as e:
        return {"status": "error", "detail": str(e), "ts": int(time.time())}

@router.get("/pipeline")
def pipeline_metrics(repos = Depends(get_repos)):
    """Full pipeline funnel: Discovery → Verification → Crawl → Jobs."""
    return repos.dashboard.get_pipeline_metrics()

@router.get("/connectors")
def connector_metrics(repos = Depends(get_repos)):
    """Per-ATS connector reliability stats."""
    return repos.dashboard.get_connector_metrics()

@router.get("/coverage")
def coverage_report(repos = Depends(get_repos)):
    """Top company coverage — which are tracked, which are missing."""
    TOP_COMPANIES = [
        "google", "microsoft", "apple", "amazon", "meta", "netflix", "nvidia",
        "salesforce", "adobe", "oracle", "uber", "airbnb", "stripe", "figma",
        "notion", "linear", "discord", "coinbase", "openai", "anthropic",
        "databricks", "snowflake", "atlassian", "zoom", "dropbox", "lyft",
        "doordash", "instacart", "robinhood", "brex", "ramp", "plaid", "gusto",
        "rippling", "airtable", "webflow", "retool", "vercel", "hashicorp",
        "gitlab", "github", "mongodb", "datadog", "pagerduty", "twilio",
        "sendgrid", "segment", "amplitude", "mixpanel", "hubspot",
    ]
    return repos.dashboard.get_coverage_report(TOP_COMPANIES)

@router.get("/tiers")
def tier_distribution(repos = Depends(get_repos)):
    """Aggregate tier distribution across all providers."""
    return repos.dashboard.get_tier_distribution()
