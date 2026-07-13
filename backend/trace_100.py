import asyncio
import time
from src.api.db import get_connection
from src.workers.company_discovery_worker import CompanyDiscoveryWorker
from src.workers.endpoint_verification_worker import EndpointVerificationWorker
from src.workers.job_crawler_worker import JobCrawlerWorker
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.workers.job_crawler_worker import make_board_from_registry_row
import logging

logging.basicConfig(level=logging.ERROR)

async def run_trace():
    conn = get_connection()
    # Get 100 benchmark companies
    rows = conn.execute("SELECT company_id FROM company_identities LIMIT 100").fetchall()
    companies = [r['company_id'] if isinstance(r, dict) else r[0] for r in rows]
    
    trace_results = []
    
    discovery_worker = CompanyDiscoveryWorker()
    validation_worker = EndpointVerificationWorker()
    
    print("=====================================================")
    print(f"Tracing {len(companies)} companies")
    print("=====================================================")
    
    for c in companies:
        result = {
            "company": c,
            "discovered": False,
            "fast_path": False,
            "verification": False,
            "crawler": False,
            "jobs_inserted": 0,
            "failure_reason": None
        }
        
        try:
            # 1. Discovery
            discovery_worker.process_item(c)
            result["discovered"] = True
            
            # Check fast path status by seeing if it's in ats_registry ACTIVE or needs validation
            reg_row = conn.execute("SELECT status FROM ats_registry WHERE company_id = %s", (c,)).fetchone()
            if reg_row:
                status = reg_row['status'] if isinstance(reg_row, dict) else reg_row[0]
                if status == 'ACTIVE':
                    result["fast_path"] = True
                
            # 2. Verification (if in endpoint_validation_queue, process it)
            # We'll just run process_item on validation_worker (it handles idempotent / skip if not needed)
            if not result["fast_path"]:
                try:
                    validation_worker.process_item(c)
                    result["verification"] = True
                except Exception as e:
                    result["failure_reason"] = f"Verification failed: {e}"
            else:
                result["verification"] = True
                
            # 3. Crawler
            reg_row = conn.execute("SELECT * FROM ats_registry WHERE company_id = %s AND status='ACTIVE'", (c,)).fetchone()
            if reg_row:
                result["crawler"] = True
                row_dict = dict(reg_row)
                board = make_board_from_registry_row(row_dict)
                session = BoardSyncSession(board, db_path="postgres")
                await session.execute()
                
                result["jobs_inserted"] = session.stats.get("jobs_inserted", 0) + session.stats.get("jobs_updated", 0)
            else:
                if not result["failure_reason"]:
                    result["failure_reason"] = "No ACTIVE registry entry after discovery/verification"
                    
        except Exception as e:
            result["failure_reason"] = f"Exception: {e}"
            
        print(f"[{result['company']}] "
              f"Disc: {result['discovered']}, "
              f"FastP: {result['fast_path']}, "
              f"Verif: {result['verification']}, "
              f"Crawl: {result['crawler']}, "
              f"Jobs: {result['jobs_inserted']}, "
              f"Fail: {result['failure_reason'] or 'None'}")
        
        trace_results.append(result)
        
    print("\n--- TRACE SUMMARY ---")
    total = len(trace_results)
    success = sum(1 for r in trace_results if r['jobs_inserted'] > 0)
    print(f"Total: {total}, Success: {success}")
    
if __name__ == '__main__':
    asyncio.run(run_trace())
