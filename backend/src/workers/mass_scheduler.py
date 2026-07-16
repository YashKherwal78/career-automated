import asyncio
import time
import json
import uuid
import traceback
import sys
import os
import random
import signal

sys.path.append('.')

from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.workers.job_crawler_worker import make_board_from_registry_row
from src.core.repositories.interfaces import SchedulerState, WorkerState, CompanyState
from src.core.repositories.scheduler.scheduler import SchedulerRepository
from src.core.repositories.scheduler.worker import WorkerRepository
from src.core.repositories.scheduler.session import SessionRepository
from src.core.repositories.provider.repository import ProviderRepository
from src.core.repositories.company.metadata import CompanyRepository
from src.core.repositories.company.state import CompanyStateRepository
from src.core.repositories.job.history import CrawlHistoryRepository

scheduler_repo = SchedulerRepository()
worker_repo = WorkerRepository()
session_repo = SessionRepository()
provider_repo = ProviderRepository()
company_repo = CompanyRepository()
state_repo = CompanyStateRepository()
history_repo = CrawlHistoryRepository()

is_draining = False

def handle_stop_signal(signum, frame):
    global is_draining
    print("\n[SCHEDULER] Received stop signal, gracefully draining workers...")
    is_draining = True
    scheduler_repo.update_state(SchedulerState.DRAINING, "1.5.0", os.getpid(), "localhost")

signal.signal(signal.SIGINT, handle_stop_signal)
signal.signal(signal.SIGTERM, handle_stop_signal)

class ProviderHealthMonitor:
    def __init__(self):
        self.rate_limit_events = {}
        self.circuit_breaker_until = {}
        self.recent_successes = {}

    def record_429(self, provider):
        if provider not in self.rate_limit_events:
            self.rate_limit_events[provider] = []
        self.rate_limit_events[provider].append(time.time())

    def record_success(self, provider):
        if provider not in self.recent_successes:
            self.recent_successes[provider] = []
        self.recent_successes[provider].append(time.time())

    def check_health_and_adjust(self, provider, min_workers, current_workers, max_workers):
        now = time.time()
        if provider in self.rate_limit_events:
            self.rate_limit_events[provider] = [t for t in self.rate_limit_events[provider] if now - t < 300]
        if provider in self.recent_successes:
            self.recent_successes[provider] = [t for t in self.recent_successes[provider] if now - t < 300]
            
        rate_limits = len(self.rate_limit_events.get(provider, []))
        successes = len(self.recent_successes.get(provider, []))
        
        if rate_limits > 10:
            print(f"[HEALTH] {provider} hit 429 threshold. Circuit breaking for 5 minutes.")
            self.circuit_breaker_until[provider] = now + 300
            self.rate_limit_events[provider] = []
            
            new_workers = max(min_workers, current_workers - 2)
            if new_workers != current_workers:
                provider_repo.update_worker_count(provider, new_workers)
            return False
            
        if now < self.circuit_breaker_until.get(provider, 0):
            return False
            
        if successes > 50 and rate_limits == 0 and current_workers < max_workers:
            new_workers = min(max_workers, current_workers + 1)
            provider_repo.update_worker_count(provider, new_workers)
            self.recent_successes[provider] = []
            
        return True

health_monitor = ProviderHealthMonitor()

def get_backoff_time(consecutive_failures):
    backoffs = [60, 120, 300, 900, 3600]
    idx = min(consecutive_failures - 1, len(backoffs) - 1)
    if idx < 0:
        idx = 0
    return backoffs[idx]

async def process_company(provider, company_id, worker_id, session_id):
    p_config = provider_repo.get_provider(provider)
    if not p_config:
        return
        
    row_data = company_repo.get_company(provider, company_id)
    if not row_data:
        return
        
    state_data = state_repo.get_state(provider, company_id)
    if not state_data:
        state_data = {}
        
    previous_jobs = state_data.get('current_jobs', 0)
    
    legacy_row = {
        "company_id": company_id,
        "provider_id": provider,
        "canonical_endpoint": row_data.get("endpoint"),
    }
    
    board = make_board_from_registry_row(legacy_row)
    connector = ConnectorRegistry.get(provider)
    if not connector:
        with state_repo.transaction() as tx:
            state_repo.update_failure(provider, company_id, {
                'status': CompanyState.FAILED,
                'error_msg': 'No connector',
                'consecutive_failures': state_data.get('consecutive_failures', 0) + 1,
                'next_crawl_offset': 86400,
                'health_score': 0.0
            }, tx)
        return
        
    session = BoardSyncSession(board, db_path="data/crm.db")
    start_time = time.time()
    
    try:
        await session.execute()
        success = session.stats.get("success", False)
        http_status = session.stats.get("http_status", 200)
        jobs_extracted = session.stats.get("jobs_inserted", 0) + session.stats.get("jobs_updated", 0)
        
        duration = time.time() - start_time
        
        if success:
            health_monitor.record_success(provider)
            job_delta = jobs_extracted - previous_jobs
            
            churn_percentage = session.stats.get("churn_percentage", 0.0)
            rolling_churn = state_data.get('rolling_churn_percent', 0.0)
            rolling_churn = (rolling_churn * 4 + churn_percentage) / 5
            
            crawls_in_tier = state_data.get('crawls_in_current_tier', 0) + 1
            current_tier = state_data.get('crawl_tier', 'NORMAL')
            
            tiers = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW', 'DORMANT']
            tier_intervals = {
                'CRITICAL': p_config.get('critical_interval', 2),
                'HIGH': p_config.get('high_interval', 4),
                'NORMAL': p_config.get('normal_interval', 8),
                'LOW': p_config.get('low_interval', 12),
                'DORMANT': p_config.get('dormant_interval', 24)
            }
            
            decision_reason = state_data.get('decision_reason', 'INITIAL_IMPORT')
            tier_changed = False
            
            manual_override = state_data.get('manual_override_enabled', 0)
            if manual_override == 1:
                interval_hours = state_data.get('manual_interval_hours', tier_intervals.get(current_tier, 8))
                decision_reason = "MANUAL_OVERRIDE"
                if state_data.get('manual_tier'):
                    current_tier = state_data.get('manual_tier')
            else:
                if crawls_in_tier >= 3:
                    if rolling_churn > p_config.get('promotion_threshold', 0.20):
                        idx = tiers.index(current_tier)
                        if idx > 0:
                            current_tier = tiers[idx - 1]
                            decision_reason = "PROMOTED_HIGH_CHURN"
                            tier_changed = True
                    elif rolling_churn < p_config.get('demotion_threshold', 0.02):
                        idx = tiers.index(current_tier)
                        if idx < len(tiers) - 1:
                            current_tier = tiers[idx + 1]
                            decision_reason = "DEMOTED_LOW_CHURN"
                            tier_changed = True
                            
                interval_hours = tier_intervals.get(current_tier, 8)
                
            if tier_changed:
                crawls_in_tier = 0
                last_tier_change = "CURRENT_TIMESTAMP"
            else:
                last_tier_change = f"'{state_data.get('last_tier_change', 'CURRENT_TIMESTAMP')}'"
                if last_tier_change == "'CURRENT_TIMESTAMP'":
                    last_tier_change = "CURRENT_TIMESTAMP"
                    
            interval_hours = max(2, min(interval_hours, 24))
            
            jitter = random.uniform(0.95, 1.05)
            next_crawl_offset = int(interval_hours * 3600 * jitter)
            
            event_id = str(uuid.uuid4())
            
            with state_repo.transaction() as tx:
                state_repo.update_success(provider, company_id, {
                    'previous_jobs': previous_jobs,
                    'current_jobs': jobs_extracted,
                    'job_delta': job_delta,
                    'next_crawl_offset': next_crawl_offset,
                    'crawl_tier': current_tier,
                    'crawl_interval_hours': interval_hours,
                    'rolling_churn_percent': rolling_churn,
                    'crawls_in_current_tier': crawls_in_tier,
                    'decision_reason': decision_reason,
                    'last_tier_change': last_tier_change
                }, tx)
                
                history_repo.insert_history(company_id, provider, {
                    'duration': duration,
                    'status': 'SUCCESS',
                    'jobs_found': jobs_extracted,
                    'session_id': session_id,
                    'crawl_event_id': event_id,
                    'jobs_inserted': session.stats.get('jobs_inserted', 0),
                    'jobs_updated': session.stats.get('jobs_updated', 0),
                    'jobs_archived': session.stats.get('jobs_archived', 0),
                    'crawl_duration_ms': duration * 1000,
                    'response_status': http_status,
                    'parser_version': getattr(connector, 'VERSION', '1.0'),
                    'connector_version': getattr(connector, 'VERSION', '1.0')
                }, tx)
                
                session_repo.record_metrics(session_id, provider, {
                    'companies_attempted': 1,
                    'companies_success': 1,
                    'jobs_discovered': jobs_extracted
                }, tx)
                
        else:
            handle_failure(provider, company_id, session.stats, http_status, session_id, duration, state_data, connector)
            
    except Exception as e:
        traceback.print_exc()
        stats = {"error_message": str(e)}
        handle_failure(provider, company_id, stats, 500, session_id, time.time() - start_time, state_data, connector)

def handle_failure(provider, company_id, stats, http_status, session_id, duration, state_data, connector):
    error_msg = stats.get("error_message", "Unknown error")
    failures = state_data.get('consecutive_failures', 0) + 1
    
    c429_inc = 0
    timeout_inc = 0
    
    if http_status == 429:
        health_monitor.record_429(provider)
        retry_after = stats.get("retry_after", 300)
        retry_after = int(retry_after * random.uniform(1.0, 1.2))
        status = CompanyState.RETRY
        offset = retry_after
        c429_inc = 1
    elif http_status == 404:
        status = CompanyState.DISABLED
        offset = 86400 * 30
    elif http_status in (401, 403):
        status = CompanyState.DISABLED
        offset = 86400 * 30
    elif "timeout" in error_msg.lower():
        status = CompanyState.RETRY
        offset = get_backoff_time(failures)
        timeout_inc = 1
    else:
        status = CompanyState.RETRY
        offset = get_backoff_time(failures)
        
    health_score = max(0.0, 100.0 - (failures * 10))
    if failures > 5:
        status = CompanyState.FAILED
        offset = 86400 * 7
        
    event_id = str(uuid.uuid4())
    
    with state_repo.transaction() as tx:
        state_repo.update_failure(provider, company_id, {
            'status': status,
            'error_msg': error_msg,
            'consecutive_failures': failures,
            'health_score': health_score,
            'next_crawl_offset': offset
        }, tx)
        
        history_repo.insert_history(company_id, provider, {
            'duration': duration,
            'status': 'FAILED',
            'error': error_msg,
            'session_id': session_id,
            'crawl_event_id': event_id,
            'crawl_duration_ms': duration * 1000,
            'response_status': http_status,
            'parser_version': getattr(connector, 'VERSION', '1.0') if connector else '1.0',
            'connector_version': getattr(connector, 'VERSION', '1.0') if connector else '1.0'
        }, tx)
        
        session_repo.record_metrics(session_id, provider, {
            'companies_attempted': 1,
            'companies_failed': 1,
            'c429_count': c429_inc,
            'timeout_count': timeout_inc
        }, tx)

async def provider_worker(provider, worker_index, config, session_id):
    worker_id = f"{provider}-worker-{worker_index}-{uuid.uuid4().hex[:6]}"
    print(f"[{worker_id}] Started in session {session_id}.")
    
    worker_repo.register_worker(worker_id, provider, 60)
    
    while True:
        if is_draining:
            print(f"[{worker_id}] Draining, exiting worker loop.")
            worker_repo.stop_worker(worker_id)
            break
            
        try:
            p_row = provider_repo.get_provider(provider)
            if not p_row or p_row.get('enabled') == 0 or worker_index >= p_row.get('current_workers'):
                print(f"[{worker_id}] Scaling down or disabled. Exiting.")
                worker_repo.stop_worker(worker_id)
                break
                
            if not health_monitor.check_health_and_adjust(provider, p_row.get('min_workers'), p_row.get('current_workers'), p_row.get('max_workers')):
                worker_repo.heartbeat(worker_id, WorkerState.IDLE)
                await asyncio.sleep(60)
                continue
            
            # Atomic lock
            # We need a custom query for finding the next queued company, so we add a method to CompanyStateRepository.
            # I will inject a raw sql lock method here or assume I added it to state_repo.
            # Actually, `acquire_next` would be better. Let's do a raw conn here inside transaction just for the lock, or use state_repo.
            
            with state_repo.transaction() as tx:
                cur = tx.execute(f"""
                    SELECT s.company_id FROM registry_{provider}_state s
                    JOIN registry_{provider} m ON s.company_id = m.company_id
                    WHERE s.status IN ('QUEUED', 'RETRY') 
                    AND s.next_crawl <= CURRENT_TIMESTAMP
                    AND s.crawl_lock = 0
                    ORDER BY m.priority DESC, s.next_crawl ASC
                    LIMIT 1
                """)
                row = cur.fetchone()
                
                if row:
                    company_id = row[0]
                    acquired = state_repo.acquire_lock(provider, company_id, worker_id, tx)
                else:
                    company_id = None
                    acquired = False
            
            if acquired:
                worker_repo.heartbeat(worker_id, WorkerState.RUNNING, company_id)
                await process_company(provider, company_id, worker_id, session_id)
            else:
                worker_repo.heartbeat(worker_id, WorkerState.IDLE)
                await asyncio.sleep(5)
                continue
                
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            print(f"[{worker_id}] Unhandled error: {e}")
            traceback.print_exc()
            await asyncio.sleep(5)

async def scheduler_main():
    active_workers = {}
    session_id = f"SESSION-{time.strftime('%Y%m%d-%H%M%S')}"
    
    scheduler_repo.update_state(SchedulerState.RUNNING, "1.5.0", os.getpid(), "localhost")
    
    providers = provider_repo.get_active_providers()
    for row in providers:
        session_repo.create_session(session_id, row['id'])
    
    print(f"Started Master Session: {session_id}")
    
    while True:
        if is_draining:
            print("[SCHEDULER] Draining: Waiting for all active workers to finish...")
            for pid, tasks in active_workers.items():
                for t in tasks:
                    if not t.done():
                        await t
            print("[SCHEDULER] All workers finished. Closing crawl session...")
            
            providers = provider_repo.get_active_providers()
            for p in providers:
                session_repo.stop_session(session_id)
                
            scheduler_repo.update_state(SchedulerState.STOPPED, "1.5.0", os.getpid(), "localhost")
            print("[SCHEDULER] Exit successful.")
            sys.exit(0)
            
        try:
            scheduler_repo.heartbeat()
            
            providers = provider_repo.get_active_providers()
            for p_row in providers:
                provider_id = p_row['id']
                current_workers = p_row['current_workers']
                
                if provider_id not in active_workers:
                    active_workers[provider_id] = []
                    
                active_workers[provider_id] = [t for t in active_workers[provider_id] if not t.done()]
                
                if not is_draining:
                    while len(active_workers[provider_id]) < current_workers:
                        idx = len(active_workers[provider_id])
                        task = asyncio.create_task(provider_worker(provider_id, idx, {}, session_id))
                        active_workers[provider_id].append(task)
                        
        except Exception as e:
            print(f"Scheduler main error: {e}")
            
        await asyncio.sleep(10)

if __name__ == "__main__":
    print("Starting Mass Scheduler...")
    asyncio.run(scheduler_main())
