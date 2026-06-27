import os
import json
import re
from dataclasses import asdict
from src.discovery.sources.greenhouse_source import GreenhouseSource
from src.discovery.eligibility_engine import EligibilityEngine
from src.crm.database import add_to_opportunity_cache, get_connection, add_to_company_registry
from src.config.config import Config

from src.discovery.providers.wellfound_provider import WellfoundProvider
from src.discovery.providers.apify_provider import ApifyProvider
from src.discovery.providers.company_intelligence_provider import CompanyIntelligenceProvider

class OpportunityAggregator:
    def __init__(self):
        # Tier 1 Priority: CompanyIntelligence, Apify, Wellfound
        self.providers = [CompanyIntelligenceProvider(), ApifyProvider(), WellfoundProvider()]
        self.greenhouse_source = GreenhouseSource()
        self.eligibility_engine = EligibilityEngine()
        
    def ensure_tables(self):
        from src.crm.database import init_db
        init_db()

    def normalize(self, opp: dict) -> dict:
        return {
            "title": opp.get("title", "Unknown Role").strip(),
            "company": opp.get("company", "Unknown Company").strip(),
            "source": opp.get("source", "Unknown"),
            "url": opp.get("url", ""),
            "ats": opp.get("ats", "UNKNOWN"),
            "location": opp.get("location", "Remote").strip(),
            "experience": opp.get("experience", "Unknown"),
            "remote": opp.get("remote", False),
            "posted_date": opp.get("posted_date", "")
        }

    def run_discovery(self):
        self.ensure_tables()
        conn = get_connection()
        cursor = conn.cursor()
        print("OpportunityAggregator: Starting V7.2 Discovery Run...")
        
        stats = {
            "seeds_discovered": 0,
            "jobs_extracted": 0,
            "eligible": 0,
            "rejected": 0,
            "companies": set()
        }
        
        all_seeds = []
        for provider in self.providers:
            try:
                seeds = provider.discover()
                all_seeds.extend(seeds)
                stats["seeds_discovered"] += len(seeds)
            except Exception as e:
                print(f"Provider {provider.__class__.__name__} failed: {e}")
                
        unique_urls = set()
        unique_seeds = []
        for seed in all_seeds:
            if seed.job_url not in unique_urls:
                unique_urls.add(seed.job_url)
                unique_seeds.append(seed)
                
                # Log discovery_strategy
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO discovery_strategy 
                        (strategy_id, provider, backend, ats, query, location, startup_filter, rule_version)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        seed.strategy_id, seed.source, "unknown", seed.ats, seed.discovered_query, "unknown", "unknown", "1.1.0"
                    ))
                    conn.commit()
                except Exception as e:
                    pass
                
        print(f"Collected {len(unique_seeds)} unique OpportunitySeeds.")
        
        final_opps = []
        for seed in unique_seeds:
            if seed.source in ("apify", "wellfound", "company_intelligence"):
                # Already fully fetched by the provider
                stats["jobs_extracted"] += 1
                stats["companies"].add(seed.company_name)
                opp = self.normalize({"title": seed.job_title, "company": seed.company_name, "url": seed.job_url, "ats": seed.ats, "source": seed.source})
                decision = self.eligibility_engine.check_eligibility(opp)
                add_to_opportunity_cache(opp, asdict(decision), strategy_id=seed.strategy_id)
                if decision.eligible:
                    stats["eligible"] += 1
                    final_opps.append(opp)
                    cursor.execute("UPDATE discovery_strategy SET eligible_opportunities = eligible_opportunities + 1 WHERE strategy_id = ?", (seed.strategy_id,))
                    conn.commit()
                else:
                    stats["rejected"] += 1
            elif seed.ats == "greenhouse":
                match = re.search(r'https://boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', seed.job_url)
                if match:
                    slug = match.group(1)
                    job_id = match.group(2)
                    jobs = self.greenhouse_source.get_job(slug, job_id)
                    if jobs:
                        stats["jobs_extracted"] += 1
                        stats["companies"].add(slug)
                        raw_opp = jobs[0]
                        opp = self.normalize(raw_opp)
                        
                        decision = self.eligibility_engine.check_eligibility(opp)
                        add_to_opportunity_cache(opp, asdict(decision), strategy_id=seed.strategy_id)
                        
                        if decision.eligible:
                            stats["eligible"] += 1
                            final_opps.append(opp)
                            add_to_company_registry(slug=slug, ats_provider="greenhouse", website=None)
                            
                            # Increment eligible count in strategy
                            cursor.execute("UPDATE discovery_strategy SET eligible_opportunities = eligible_opportunities + 1 WHERE strategy_id = ?", (seed.strategy_id,))
                            conn.commit()
                        else:
                            stats["rejected"] += 1
                    
        conn.close()
        print(f"Discovery Complete! Extracted {stats['jobs_extracted']} jobs.")
        print(f"Eligible: {stats['eligible']} | Rejected: {stats['rejected']}")
        
        return final_opps, stats
