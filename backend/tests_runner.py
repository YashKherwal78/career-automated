import sqlite3
import asyncio
import sys
import logging
import json
import time

sys.path.append('.')
logging.basicConfig(level=logging.INFO)

COMPANIES = [
    {"domain": "vercel.com", "name": "Vercel", "id": "vercel"},
    {"domain": "segment.com", "name": "Segment", "id": "segment"},
    {"domain": "plaid.com", "name": "Plaid", "id": "plaid-com-05ed3e"},
    {"domain": "rippling.com", "name": "Rippling", "id": "rippling-com-1b7f57"},
    {"domain": "benchling.com", "name": "Benchling", "id": "benchling"},
]

async def run_pipeline_for_company(company_domain, company_name, company_id):
    print(f"\n======================================")
    print(f"RUNNING FOR {company_domain} (ID: {company_id})")
    print(f"======================================")
    conn = sqlite3.connect('data/crm.db', isolation_level=None)
    conn.row_factory = sqlite3.Row
    
    # Reset registry and jobs for company
    conn.execute("DELETE FROM ats_registry WHERE company_id=?", (company_id,))
    conn.execute("DELETE FROM normalized_jobs WHERE company_id=?", (company_id,))
    conn.execute("DELETE FROM endpoint_candidates WHERE company_id=?", (company_id,))
    conn.execute("DELETE FROM local_queues")
    
    conn.execute("UPDATE company_identities SET lifecycle_state='DISCOVERED' WHERE company_id=?", (company_id,))
    
    print(f'--- 1. Running Discovery (V3) ---')
    from src.discovery.pipeline.sources import HeadProbeSource, StaticLandingPageSource, ExternalSearchSource, HeuristicTokenSource
    from src.discovery.pipeline.plugins.greenhouse_plugin import GreenhouseDiscoveryPlugin
    from src.discovery.pipeline.plugins.lever_plugin import LeverDiscoveryPlugin
    from src.discovery.pipeline.plugins.workday_plugin import WorkdayDiscoveryPlugin
    from src.discovery.pipeline.plugins.ashby_plugin import AshbyDiscoveryPlugin
    from src.discovery.pipeline.plugins.workable_plugin import WorkableDiscoveryPlugin
    from src.discovery.pipeline.plugins.smartrecruiters_plugin import SmartRecruitersDiscoveryPlugin
    from src.discovery.pipeline.plugins.teamtailor_plugin import TeamtailorDiscoveryPlugin
    from src.discovery.pipeline.plugins.breezy_plugin import BreezyDiscoveryPlugin
    from src.discovery.pipeline.fallback_models import DiscoveryBudget
    from src.discovery.pipeline.discovery_orchestrator import DiscoveryOrchestrator

    sources = [HeadProbeSource(), StaticLandingPageSource(), ExternalSearchSource(), HeuristicTokenSource()]
    plugins = [
        GreenhouseDiscoveryPlugin(), LeverDiscoveryPlugin(), WorkdayDiscoveryPlugin(), 
        AshbyDiscoveryPlugin(), WorkableDiscoveryPlugin(), SmartRecruitersDiscoveryPlugin(), 
        TeamtailorDiscoveryPlugin(), BreezyDiscoveryPlugin()
    ]
    orchestrator = DiscoveryOrchestrator(sources=sources, plugins=plugins)
    budget = DiscoveryBudget(max_http_requests=20, max_search_queries=2, max_latency_seconds=30.0)

    try:
        res = await orchestrator.execute(
            company=company_name, 
            website=f'https://{company_domain}', 
            budget=budget,
            company_id=company_id
        )
        all_candidates = res.get('all_candidates', [])
    except Exception as e:
        print(f"DiscoveryOrchestrator failed: {e}")
        all_candidates = []
    
    cursor = conn.cursor()
    for pr in all_candidates:
        provider_id = getattr(pr, 'provider_id', pr.candidate.provider_id if hasattr(pr, 'candidate') else getattr(pr, 'ats_domain', 'unknown').split('.')[0])
        url = pr.url if hasattr(pr, 'url') else pr.candidate.url
        evidence = [e.__dict__ for e in (pr.evidence if hasattr(pr, 'evidence') else [])]
        confidence_score = getattr(pr, 'confidence_score', getattr(pr, 'normalized_score', 0))
        cursor.execute('''
            INSERT INTO endpoint_candidates (company_id, provider_id, url, discovery_source, evidence, confidence_score, lifecycle_state)
            VALUES (?, ?, ?, ?, ?, ?, 'VERIFYING')
        ''', (company_id, provider_id, url, "DiscoveryOrchestrator", json.dumps(evidence), confidence_score))
        
    cursor.execute('''
        INSERT INTO local_queues (queue_name, payload, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', ('verification_queue', json.dumps({'company_id': company_id})))
    
    conn.execute("UPDATE company_identities SET lifecycle_state='VERIFICATION_PENDING' WHERE company_id=?", (company_id,))
    
    print(f'--- 2. Running Verification Worker ---')
    from src.workers.endpoint_verification_worker import EndpointVerificationWorker
    verifier = EndpointVerificationWorker()
    q_item = verifier.queue.pop('verification_queue')
    if q_item:
        print('Popped verification queue!')
        verifier.queue.push('verification_queue', q_item['payload'])
        task = asyncio.create_task(verifier.run_async())
        for _ in range(30):
            await asyncio.sleep(1)
            row = conn.execute("SELECT * FROM ats_registry WHERE company_id=?", (company_id,)).fetchone()
            if row:
                break
        task.cancel()
    
    row = conn.execute("SELECT * FROM ats_registry WHERE company_id=?", (company_id,)).fetchone()
    print(f'ATS Registry:', dict(row) if row else None)
    
    if not row:
        print(f"FAILED TO VERIFY {company_domain}")
        conn.close()
        return False
        
    print(f'--- 3. Running JobCrawler Worker ---')
    from src.workers.job_crawler_worker import JobCrawlerWorker
    worker = JobCrawlerWorker()
    
    row_data = conn.execute("SELECT * FROM ats_registry WHERE company_id=?", (company_id,)).fetchone()
    if not row_data:
        print('Board missing!')
        conn.close()
        return False

    board_dict = dict(row_data)
    print(f'Fetched board for {company_id}:', board_dict)
    from src.discovery.pipeline.sync_session import BoardSyncSession
    from src.workers.job_crawler_worker import make_board_from_registry_row
    
    board = make_board_from_registry_row(board_dict)
    session = BoardSyncSession(board, db_path=worker.db_path)
    
    await session.execute()
    print(f'Worker stats:', session.stats)
        
    coverage = conn.execute("SELECT count(*) FROM normalized_jobs WHERE company_id=?", (company_id,)).fetchone()[0]
    print(f'DB Coverage:', coverage)
    
    conn.close()
    return session.stats.get("success", False) and coverage > 0

async def main():
    results = {}
    for c in COMPANIES:
        try:
            res = await run_pipeline_for_company(c["domain"], c["name"], c["id"])
            results[c["domain"]] = res
        except Exception as e:
            print(f"CRASH on {c['domain']}: {e}")
            results[c["domain"]] = False
            
    print("\n\n=== FINAL RESULTS ===")
    for domain, success in results.items():
        print(f"{domain}: {'PASS' if success else 'FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
