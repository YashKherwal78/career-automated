import sqlite3
import time
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional

from src.discovery.pipeline.discovery_orchestrator import DiscoveryOrchestrator
from src.discovery.pipeline.sources import HeadProbeSource, StaticLandingPageSource, ExternalSearchSource
from src.discovery.pipeline.plugins.greenhouse_plugin import GreenhouseDiscoveryPlugin
from src.discovery.pipeline.plugins.lever_plugin import LeverDiscoveryPlugin
from src.discovery.pipeline.plugins.workday_plugin import WorkdayDiscoveryPlugin
from src.discovery.pipeline.plugins.ashby_plugin import AshbyDiscoveryPlugin
from src.discovery.pipeline.caches import ReplayCache
from src.discovery.pipeline.fallback_models import DiscoveryBudget

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ContinuousDiscoveryEngine')

class DiscoveryDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

class ContinuousDiscoveryEngine:
    def __init__(self, db_path: str):
        self.db = DiscoveryDB(db_path)
        
        # Instantiate orchestrator with HeadProbe, StaticPage, and Search sources,
        # along with Greenhouse, Lever, and Workday discovery plugins.
        sources = [HeadProbeSource(), StaticLandingPageSource(), ExternalSearchSource()]
        plugins = [
            GreenhouseDiscoveryPlugin(),
            LeverDiscoveryPlugin(),
            WorkdayDiscoveryPlugin(),
            AshbyDiscoveryPlugin(),   # root cause of Notion/Linear 0% — added C1B.6
        ]
        replay_cache = ReplayCache(db_path)
        
        self.orchestrator = DiscoveryOrchestrator(
            sources=sources,
            plugins=plugins,
            replay_cache=replay_cache
        )
        
    async def run(self, limit: Optional[int] = None) -> Dict[str, Any]:
        logger.info("Starting Continuous Company Discovery Engine...")
        
        # 1. Fetch companies to process from company_identities
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT company_id, legal_name, website, domain FROM company_identities")
            companies = [dict(row) for row in cursor.fetchall()]
            
        total_companies = len(companies)
        logger.info(f"Loaded {total_companies} company identities from database.")
        
        metrics = {
            "companies_processed": 0,
            "registry_hits": 0,
            "homepage_discoveries": 0,
            "greenhouse_discoveries": 0,
            "lever_discoveries": 0,
            "ashby_discoveries": 0,
            "workable_discoveries": 0,
            "ddg_discoveries": 0,
            "exa_discoveries": 0,
            "verified": 0,
            "failed_discoveries": 0,
            "jobs_crawled": 0,
            "jobs_crawled": 0,
            "processed": 0,
            "funnel": {
                "generated": 0,
                "parsed": 0,
                "score_passed": 0,
                "validation_passed": 0,
                "inspected": 0,
                "skipped_score": 0,
                "skipped_validation": 0,
                "skipped_budget": 0
            }
        }
        
        # Track started time
        start_time = time.time()
        
        processed_count = 0
        for company in companies:
            # Check configured limit
            if limit is not None and processed_count >= limit:
                break
                
            company_id = company["company_id"]
            company_name = company["legal_name"] or company_id
            
            # Check if ACTIVE endpoint already exists in ats_registry
            active_endpoint = self.orchestrator.registry.get_active_endpoint(company_id)
            if active_endpoint:
                metrics["registry_hits"] += 1
                metrics["companies_processed"] += 1
                continue
                
            # Perform discovery on new companies
            processed_count += 1
            metrics["processed"] += 1
            metrics["companies_processed"] += 1
            
            website = company.get("website") or company.get("domain")
            if not website:
                metrics["failed_discoveries"] += 1
                continue
                
            if not website.startswith("http"):
                website = f"https://{website}"
                
            logger.info(f"[{processed_count}] Discovering: {company_name} ({website})")
            
            # Budget parameters
            budget = DiscoveryBudget(max_http_requests=25, max_latency_seconds=30.0, max_search_queries=5)
            
            try:
                res = await self.orchestrator.execute(company_id, website, budget)
                verified = res.get("verified", [])
                all_candidates = res.get("all_candidates", [])
                funnel = res.get("funnel", {})
                
                # Accumulate funnel metrics
                for k, v in funnel.items():
                    if k in metrics["funnel"] and isinstance(v, (int, float)):
                        metrics["funnel"][k] += v

                if verified:
                    metrics["verified"] += 1
                    best_candidate = verified[0]
                    
                    # Extract source and provider info
                    top_source = "Unknown"
                    if best_candidate.evidence:
                        top_source = sorted(best_candidate.evidence, key=lambda e: e.weight, reverse=True)[0].source
                        
                    if "HeadProbe" in top_source or "StaticLandingPage" in top_source:
                        metrics["homepage_discoveries"] += 1
                    elif "DDG" in top_source:
                        metrics["ddg_discoveries"] += 1
                    elif "Exa" in top_source:
                        metrics["exa_discoveries"] += 1
                        
                    # Map plugin types
                    plugin_name = best_candidate.plugin_name.lower() if hasattr(best_candidate, 'plugin_name') else ""
                    if "greenhouse" in plugin_name:
                        metrics["greenhouse_discoveries"] += 1
                    elif "lever" in plugin_name:
                        metrics["lever_discoveries"] += 1
                    elif "workday" in plugin_name:
                        # Workday plugin is used
                        pass
                else:
                    metrics["failed_discoveries"] += 1
            except Exception as e:
                logger.error(f"Failed discovering {company_name}: {e}")
                metrics["failed_discoveries"] += 1
                
        metrics["total_elapsed_sec"] = time.time() - start_time
        return metrics
