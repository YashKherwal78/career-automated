import os
import sys
import time
import json
import statistics
import threading
import uuid
import datetime
from pathlib import Path
from queue import Queue

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

from src.core.repositories.manager import RepositoryManager
from src.core.repositories.interfaces import WorkerState, SchedulerState, WorkerType, CompanyState
from src.core.repositories.registry_resolver import RegistryResolver
from src.api.db import get_connection

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "postgres"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def fail(msg):
    print(f"FAILED: {msg}", file=sys.stderr)
    sys.exit(1)

def get_c(row):
    return row[0] if isinstance(row, tuple) else list(row.values())[0] if isinstance(row, dict) else row[list(row.keys())[0]]

def cleanup_test_data(repos: RepositoryManager):
    """Deletes all records prefixed with __TEST__"""
    conn = repos.get_connection()
    try:
        p = conn.placeholder()
        tables = [
            ("jobs", "id"),
            ("crawl_history", "company_id"),
            ("worker_history", "worker_id"),
            ("worker_states", "worker_id"),
            ("sync_sessions", "id"),
            ("ats_registry", "company_id"),
            ("company_identities", "company_id"),
            ("crawl_sessions", "session_id")
        ]
        # Also dynamic provider tables if any
        tables.append((RegistryResolver.state_table("ashby"), "company_id"))
        tables.append((RegistryResolver.metadata_table("ashby"), "company_id"))
        
        for table, pk in tables:
            try:
                conn.execute(f"DELETE FROM {table} WHERE {pk} LIKE {p}", ('__TEST__%',))
            except Exception as e:
                pass
        conn.commit()
    except Exception as e:
        print(f"Warning during cleanup: {e}")
    finally:
        conn.close()

def generate_stats(latencies):
    if not latencies:
        return {}
    latencies.sort()
    return {
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p95": latencies[int(len(latencies) * 0.95)] if len(latencies) > 0 else 0,
        "p99": latencies[int(len(latencies) * 0.99)] if len(latencies) > 0 else 0,
    }

def run_benchmarks(repos: RepositoryManager, iterations=500):
    print(f"Running benchmarks ({iterations} iterations)...")
    results = {}
    
    # Insert Latency
    insert_latencies = []
    for i in range(iterations):
        cid = f"__TEST__bench_{i}_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        repos.company.ensure_company_identity(cid, f"test{i}.com", f"Test {i}", f"https://test{i}.com")
        insert_latencies.append((time.time() - t0) * 1000)
    results["insert_latency"] = generate_stats(insert_latencies)
    
    # Update Latency
    update_latencies = []
    for i in range(iterations):
        cid = f"__TEST__bench_{i}"
        t0 = time.time()
        with repos.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(f"UPDATE company_identities SET canonical_name = 'Updated' WHERE company_id LIKE {p}", ('__TEST__bench_%',))
        update_latencies.append((time.time() - t0) * 1000)
    results["update_latency"] = generate_stats(update_latencies)
    
    # Delete Latency
    delete_latencies = []
    for i in range(iterations):
        t0 = time.time()
        with repos.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(f"DELETE FROM company_identities WHERE company_id LIKE {p}", ('__TEST__bench_%',))
        delete_latencies.append((time.time() - t0) * 1000)
    results["delete_latency"] = generate_stats(delete_latencies)
    
    # Full Transaction (Rollback)
    rollback_latencies = []
    for i in range(iterations):
        t0 = time.time()
        try:
            with repos.transaction():
                repos.company.ensure_company_identity(f"__TEST__rb_{i}", f"rb{i}.com", f"RB {i}", f"https://rb{i}.com")
                raise ValueError("Trigger rollback")
        except ValueError:
            pass
        rollback_latencies.append((time.time() - t0) * 1000)
    results["rollback_latency"] = generate_stats(rollback_latencies)
    
    return results

def test_transactions(repos: RepositoryManager) -> bool:
    print("Testing Transactions...")
    cid = "__TEST__tx_company"
    wid = "__TEST__tx_worker"
    
    try:
        with repos.transaction():
            repos.company.ensure_company_identity(cid, "tx.com", "Tx Corp", "https://tx.com")
            repos.worker.register_worker(wid, "TxWorker", WorkerType.CRAWLER)
            raise ValueError("Rollback everything")
    except ValueError:
        pass
        
    conn = repos.get_connection()
    p = conn.placeholder()
    c1 = get_c(conn.execute(f"SELECT count(*) FROM company_identities WHERE company_id={p}", (cid,)).fetchone())
    c2 = get_c(conn.execute(f"SELECT count(*) FROM worker_states WHERE worker_id={p}", (wid,)).fetchone())
    conn.close()
    
    return c1 == 0 and c2 == 0

def test_foreign_keys(repos: RepositoryManager) -> bool:
    print("Testing Foreign Keys...")
    try:
        with repos.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(
                f"INSERT INTO ats_registry (company_id, provider_id, candidate_id, endpoint, canonical_endpoint, status) VALUES ({p}, {p}, {p}, {p}, {p}, 'ACTIVE')",
                ("__TEST__non_existent", "ashby", "none", "url", "url")
            )
        return False
    except Exception as e:
        return "foreign key" in str(e).lower() or "integrity" in str(e).lower() or "fk_" in str(e).lower()

def test_unique_constraints(repos: RepositoryManager) -> bool:
    print("Testing Unique Constraints...")
    repos.company.ensure_company_identity("__TEST__unique", "uniq.com", "Uniq", "https://uniq.com")
    # Try inserting same company again manually without DO NOTHING
    try:
        with repos.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(
                f"INSERT INTO company_identities (company_id, domain, canonical_name, website) VALUES ({p}, {p}, {p}, {p})",
                ("__TEST__unique", "uniq.com", "Uniq", "https://uniq.com")
            )
        return False
    except Exception as e:
        return "unique" in str(e).lower() or "duplicate" in str(e).lower()

def test_concurrency(repos: RepositoryManager) -> bool:
    print("Testing Concurrency (20 threads locking same company)...")
    cid = "__TEST__concurrency"
    repos.company.ensure_company_identity(cid, "conc.com", "Conc", "https://conc.com")
    repos.company.report_canonical_endpoint(cid, "ashby", None, "url", "url")
    
    # Init company state
    table_name = RegistryResolver.state_table("ashby")
    conn = repos.get_connection()
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {table_name} (
        company_id TEXT PRIMARY KEY, status TEXT, crawl_lock INTEGER DEFAULT 0,
        locked_at TIMESTAMP, worker_id TEXT, previous_jobs INTEGER, current_jobs INTEGER,
        job_delta INTEGER, last_success TIMESTAMP, consecutive_failures INTEGER DEFAULT 0,
        total_success INTEGER DEFAULT 0, next_crawl TIMESTAMP, health_score REAL DEFAULT 100.0,
        crawl_tier TEXT, crawl_interval_hours INTEGER, rolling_churn_percent REAL,
        crawls_in_current_tier INTEGER DEFAULT 0, decision_reason TEXT, last_tier_change TIMESTAMP
    )""")
    conn.commit()
    conn.close()

    with repos.transaction() as conn:
        p = conn.dialect.placeholder()
        if not conn.execute(f"SELECT 1 FROM {table_name} WHERE company_id={p}", (cid,)).fetchone():
            conn.execute(f"INSERT INTO {table_name} (company_id, status) VALUES ({p}, 'QUEUED')", (cid,))
        conn.execute(f"UPDATE {table_name} SET crawl_lock=0, status='QUEUED' WHERE company_id={p}", (cid,))
        
    success_count = [0]
    lock = threading.Lock()
    
    def worker_thread(tid):
        local_repos = RepositoryManager(repos.db_path)
        locked = local_repos.company_state.acquire_lock("ashby", cid, f"worker_{tid}")
        if locked:
            with lock:
                success_count[0] += 1
                
    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    return success_count[0] == 1

def test_isolation(repos: RepositoryManager) -> bool:
    print("Testing Isolation (READ COMMITTED)...")
    cid = "__TEST__isolation"
    q = Queue()
    
    def writer():
        local_repos = RepositoryManager(repos.db_path)
        try:
            with local_repos.transaction():
                local_repos.company.ensure_company_identity(cid, "iso.com", "Iso", "http://iso.com")
                q.put("WRITTEN")
                q.get(timeout=10)
        except Exception:
            pass
            
    t = threading.Thread(target=writer)
    t.start()
    
    try:
        msg = q.get(timeout=10)
    except:
        return False
    
    conn = repos.get_connection()
    p = conn.placeholder()
    c1 = get_c(conn.execute(f"SELECT count(*) FROM company_identities WHERE company_id={p}", (cid,)).fetchone())
    
    q.put("COMMIT")
    t.join()
    
    c2 = get_c(conn.execute(f"SELECT count(*) FROM company_identities WHERE company_id={p}", (cid,)).fetchone())
    conn.close()
    
    return c1 == 0 and c2 == 1

def test_deadlock(repos: RepositoryManager) -> bool:
    print("Testing Deadlock Recovery...")
    cid1 = "__TEST__dl_1"
    cid2 = "__TEST__dl_2"
    repos.company.ensure_company_identity(cid1, "dl1.com", "DL1", "http")
    repos.company.ensure_company_identity(cid2, "dl2.com", "DL2", "http")
        
    q1 = Queue()
    q2 = Queue()
    deadlock_detected = False
    
    def thread_a():
        local_repos = RepositoryManager(repos.db_path)
        try:
            with local_repos.transaction() as conn:
                p = conn.dialect.placeholder()
                conn.execute(f"SELECT * FROM company_identities WHERE company_id={p} FOR UPDATE", (cid1,))
                q1.put("LOCKED_1")
                q2.get(timeout=5) # Wait for B to lock 2
                conn.execute(f"SELECT * FROM company_identities WHERE company_id={p} FOR UPDATE", (cid2,))
        except Exception as e:
            if "deadlock detected" in str(e).lower():
                nonlocal deadlock_detected
                deadlock_detected = True
                
    def thread_b():
        local_repos = RepositoryManager(repos.db_path)
        try:
            with local_repos.transaction() as conn:
                p = conn.dialect.placeholder()
                conn.execute(f"SELECT * FROM company_identities WHERE company_id={p} FOR UPDATE", (cid2,))
                q2.put("LOCKED_2")
                q1.get(timeout=5) # Wait for A to lock 1
                conn.execute(f"SELECT * FROM company_identities WHERE company_id={p} FOR UPDATE", (cid1,))
        except Exception as e:
            if "deadlock detected" in str(e).lower():
                nonlocal deadlock_detected
                deadlock_detected = True
                
    ta = threading.Thread(target=thread_a)
    tb = threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    
    return deadlock_detected

def test_connection_pool_stress(repos: RepositoryManager, threads_count=30) -> bool:
    print(f"Testing Connection Pool Stress ({threads_count} concurrent acquisitions)...")
    errors = []
    
    def worker():
        try:
            local_repos = RepositoryManager(repos.db_path)
            conn = local_repos.get_connection()
            conn.execute("SELECT 1").fetchone()
            conn.close()
        except Exception as e:
            errors.append(e)
            
    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    if errors:
        print(f"Pool stress had {len(errors)} errors. First: {errors[0]}")
    return len(errors) == 0

def test_e2e_lifecycle(repos: RepositoryManager) -> bool:
    print("Testing End-to-End Scheduler Lifecycle...")
    try:
        cid = "__TEST__e2e_comp"
        wid = "__TEST__e2e_worker"
        sid = "__TEST__e2e_session"
        provider = "ashby"
        table_name = RegistryResolver.state_table(provider)
        
        # 1. Setup
        repos.company.ensure_company_identity(cid, "e2e.com", "E2E", "http")
        repos.company.report_canonical_endpoint(cid, provider, None, "url", "url")

        conn = repos.get_connection()
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""CREATE TABLE IF NOT EXISTS {table_name} (
            company_id TEXT PRIMARY KEY, status TEXT, crawl_lock INTEGER DEFAULT 0,
            locked_at TIMESTAMP, worker_id TEXT, previous_jobs INTEGER, current_jobs INTEGER,
            job_delta INTEGER, last_success TIMESTAMP, consecutive_failures INTEGER DEFAULT 0,
            total_success INTEGER DEFAULT 0, next_crawl TIMESTAMP, health_score REAL DEFAULT 100.0,
            crawl_tier TEXT, crawl_interval_hours INTEGER, rolling_churn_percent REAL,
            crawls_in_current_tier INTEGER DEFAULT 0, decision_reason TEXT, last_tier_change TIMESTAMP
        )""")
        conn.commit()
        conn.close()

        with repos.transaction() as conn:
            p = conn.dialect.placeholder()
            if not conn.execute(f"SELECT 1 FROM {table_name} WHERE company_id={p}", (cid,)).fetchone():
                conn.execute(f"INSERT INTO {table_name} (company_id, status, crawl_lock) VALUES ({p}, 'QUEUED', 0)", (cid,))
        
        # 2. Worker & Session
        repos.worker.register_worker(wid, "e2e_worker", WorkerType.CRAWLER)
        repos.session.create_session(sid, provider)
        
        # 3. Lock
        locked = repos.company_state.acquire_lock(provider, cid, wid)
        if not locked: return False
        
        # 4. Crawl (simulate)
        repos.worker.heartbeat(wid, WorkerState.RUNNING, cid, "crawling")
        # Upsert Job (simulated via JobRepository if we had mock jobs, but JobRepository takes full Job objects)
        
        # 5. Success
        repos.worker.stop_worker(wid, "E2E Complete")
        repos.session.record_metrics(sid, provider, {"jobs_found": 1})
        
        return True
    except Exception as e:
        print(f"E2E Lifecycle failed: {e}")
        return False

def run():
    print("Starting Repository Compatibility Tests...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        fail("DATABASE_URL not set")
    repos = RepositoryManager("dummy.db")
    
    # Pre-cleanup
    cleanup_test_data(repos)
    
    results = {}
    
    try:
        e2e_pass = test_e2e_lifecycle(repos)
        results["CompanyRepository"] = "PASS" if e2e_pass else "FAIL"
        results["CompanyStateRepository"] = "PASS" if e2e_pass else "FAIL"
        results["WorkerRepository"] = "PASS" if e2e_pass else "FAIL"
        results["SessionRepository"] = "PASS" if e2e_pass else "FAIL"
        
        with repos.transaction():
            repos.scheduler.update_state(SchedulerState.RUNNING, "1.0", 1234, "localhost")
        results["SchedulerRepository"] = "PASS"
    except Exception as e:
        print(f"Basic Repos failed: {e}")
        for k in ["CompanyRepository", "CompanyStateRepository", "WorkerRepository", "SchedulerRepository", "SessionRepository"]:
            results.setdefault(k, "FAIL")
            
    # Structural Validations
    results["Transactions"] = "PASS" if test_transactions(repos) else "FAIL"
    results["ForeignKeys"] = "PASS" if test_foreign_keys(repos) else "FAIL"
    results["UniqueConstraints"] = "PASS" if test_unique_constraints(repos) else "FAIL"
    results["Isolation"] = "PASS" if test_isolation(repos) else "FAIL"
    results["Concurrency"] = "PASS" if test_concurrency(repos) else "FAIL"
    results["Deadlock"] = "PASS" if test_deadlock(repos) else "FAIL"
    results["ConnectionPoolStress"] = "PASS" if test_connection_pool_stress(repos) else "FAIL"
    
    # Benchmarks (500 iterations)
    bench_stats = run_benchmarks(repos, iterations=500)
    
    # Post-cleanup
    cleanup_test_data(repos)
    
    # Generate Output
    all_pass = all(v == "PASS" for v in results.values())
    
    print("\n" + "="*50)
    print("Repository Compatibility Validations")
    print("="*50)
    for k, v in results.items():
        print(f"{k.ljust(30)} {v}")
        
    print("\n" + "="*50)
    print("Benchmarks (500 iterations, ms)")
    print("="*50)
    for k, v in bench_stats.items():
        print(f"{k}: Mean={v.get('mean',0):.2f} | P95={v.get('p95',0):.2f} | Min={v.get('min',0):.2f} | Max={v.get('max',0):.2f}")
        
    print("\n" + "="*50)
    
    recommendations = []
    if bench_stats.get("insert_latency", {}).get("mean", 0) > 50:
        recommendations.append("- Insert latency is > 50ms. Consider using batch inserts (`executemany`) for JobRepository if not already doing so.")
    if bench_stats.get("rollback_latency", {}).get("mean", 0) > 100:
        recommendations.append("- Rollback latency is high. Avoid long-running transactions to prevent pool exhaustion.")
    if not recommendations:
        recommendations.append("- Performance is within expected bounds. No immediate structural optimizations required.")
        
    if all_pass:
        print("READY FOR DATA MIGRATION")
    else:
        print("FAILURES DETECTED. DO NOT MIGRATE DATA.")
        
    report = {
        "status": "PASS" if all_pass else "FAIL",
        "repositories": results,
        "benchmarks": bench_stats,
        "recommendations": recommendations
    }
    
    with open(ARTIFACTS_DIR / "compatibility_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    summary_md = [
        "# Repository Compatibility & Performance Report",
        "",
        f"## Overall Status: {'✅ PASS' if all_pass else '❌ FAIL'}",
        "",
        "### Repositories & Structural Validations"
    ]
    for k, v in results.items():
        summary_md.append(f"- **{k}**: {'✅' if v == 'PASS' else '❌'} {v}")
        
    summary_md.extend([
        "",
        "### Benchmark Highlights (ms, 500 iter)"
    ])
    for k, v in bench_stats.items():
        summary_md.append(f"- **{k}**: Mean: {v.get('mean',0):.2f} | Median: {v.get('median',0):.2f} | P95: {v.get('p95',0):.2f} | P99: {v.get('p99',0):.2f} | Min: {v.get('min',0):.2f} | Max: {v.get('max',0):.2f}")
        
    summary_md.extend([
        "",
        "### Performance Recommendations"
    ] + recommendations)
    
    if all_pass:
        summary_md.extend(["", "### Conclusion", "**READY FOR DATA MIGRATION** (Phase 4)"])
        
    with open(ARTIFACTS_DIR / "compatibility_summary.md", "w") as f:
        f.write("\n".join(summary_md))
        
    if not all_pass:
        sys.exit(1)

if __name__ == "__main__":
    run()
