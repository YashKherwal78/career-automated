import asyncio
import os
import sys
import sqlite3
import time
import json
import traceback

sys.path.append('.')

from src.api.db import get_connection
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.workers.job_crawler_worker import make_board_from_registry_row
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.pipeline_state_manager import PipelineStateManager
from src.discovery.pipeline.telemetry import Telemetry

async def run_production():
    print("Fetching active companies from ats_registry...")
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM ats_registry WHERE status='ACTIVE'")
        companies = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    print(f"Found {len(companies)} active companies.")
    
    results = []
    
    for row_data in companies:
        company_id = row_data["company_id"]
        provider_id = row_data["provider_id"]
        print(f"\n======================================")
        print(f"RUNNING PIPELINE FOR {company_id} ({provider_id})")
        print(f"======================================")

        try:
            board = make_board_from_registry_row(row_data)
            connector = ConnectorRegistry.get(board.provider)
            session = BoardSyncSession(board, db_path="data/crm.db")
            
            # Transition to CRAWL_PENDING then CRAWLING
            try:
                PipelineStateManager.transition(company_id, "CRAWL_PENDING")
                PipelineStateManager.transition(company_id, "CRAWLING")
            except Exception as e:
                print(f"State transition error (ignoring): {e}")
            
            start_time = time.time()
            
            await session.execute()
            
            success = session.stats.get("success", False)
            job_count = session.stats.get("jobs_inserted", 0) + session.stats.get("jobs_updated", 0)
            
            if success:
                PipelineStateManager.transition(company_id, "ACTIVE", crawl_status="SUCCESS")
            else:
                PipelineStateManager.transition(company_id, "CRAWL_FAILED", failure_reason="SYNC_EXECUTION_FAILURE", crawl_status="FAILED")
            
            duration = time.time() - start_time
            print(f"Stats for {company_id}: {session.stats}")
            
            res = {
                "company_id": company_id,
                "provider": provider_id,
                "endpoint": row_data.get("canonical_endpoint") or row_data.get("endpoint"),
                "planner_decision": session.stats.get("planner_decision", "unknown"),
                "connector": connector.__class__.__name__ if connector else "None",
                "requests_made": session.stats.get("http_requests", 0),
                "pages_crawled": session.stats.get("pages_crawled", 0),
                "jobs_extracted": session.stats.get("jobs_found", 0),
                "jobs_inserted": job_count,
                "execution_time": duration,
                "success": success
            }
            results.append(res)
            
            if not success:
                print(f"FAILURE detected for {company_id}! Stopping.")
                break

        except Exception as e:
            traceback.print_exc()
            try:
                PipelineStateManager.transition(company_id, "CRAWL_FAILED", failure_reason=type(e).__name__, crawl_status="FAILED")
            except:
                pass
            print(f"FAILURE detected for {company_id}! Stopping.")
            break
            
    print("\n\nAll done.")

if __name__ == "__main__":
    asyncio.run(run_production())
