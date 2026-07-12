import os
import sys
import time
import csv
import sqlite3
import logging
import json
from urllib.parse import urlparse
from src.config.settings import settings
from src.workers.worker_base import BaseWorker
from src.discovery.pipeline.telemetry import Telemetry, Stage, Status, ReasonCode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CompanyDiscoveryWorker")

def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return ""

class CompanyDiscoveryWorker(BaseWorker):
    def __init__(self):
        super().__init__("CompanyDiscoveryWorker")

    def run(self):
        logger.info(f"CompanyDiscoveryWorker starting as {self.worker_id}")
        while self.running:
            try:
                processed_count = 0
                # 1. Parse CSV seeds
                csv_path = os.path.join(os.getcwd(), "benchmark", "companies.csv")
                if os.path.exists(csv_path):
                    with open(csv_path, mode='r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                            conn.row_factory = sqlite3.Row
                            for row in reader:
                                name = row.get("company", "").strip()
                                website = row.get("website", "").strip()
                                if not name or not website:
                                    continue
                                
                                domain = extract_domain(website)
                                company_id = name.lower().replace(" ", "-")

                                # Check if company_id already exists
                                cursor = conn.execute("SELECT 1 FROM company_identities WHERE company_id = ?", (company_id,))
                                if not cursor.fetchone():
                                    conn.execute('''
                                        INSERT OR IGNORE INTO company_identities (company_id, domain, canonical_name, website)
                                        VALUES (?, ?, ?, ?)
                                    ''', (company_id, domain, name, website))
                                    conn.commit()
                                    
                                    # Emit event
                                    self.metrics.record_event("CompanyDiscovered", {
                                        "company_id": company_id,
                                        "name": name,
                                        "website": website,
                                        "domain": domain,
                                        "worker_id": self.worker_id
                                    })
                                    
                                    logger.info(f"Discovered new company: {name} ({company_id})")
                                    processed_count += 1

                # 2. Feeder - Check if we can fast-path, else push to discovery_queue
                from src.discovery.pipeline.fast_path_registry import FastPathRegistry
                fast_patcher = FastPathRegistry(self.db_path)
                
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute('''
                        SELECT i.company_id, i.canonical_name, i.domain, i.website, i.aliases
                        FROM company_identities i
                        LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
                        WHERE r.company_id IS NULL
                    ''')
                    candidates = [dict(row) for row in cursor.fetchall()]

                    for cand in candidates:
                        cid = cand["company_id"]
                        
                        # Try parsing aliases JSON
                        aliases_str = cand.get("aliases")
                        metadata = {}
                        if aliases_str:
                            try:
                                metadata = json.loads(aliases_str)
                            except Exception:
                                pass
                        
                        fast_pathed = False
                        if metadata.get("source") == "jobhive":
                            fast_pathed = fast_patcher.fast_path_company(
                                company_id=cid,
                                canonical_name=cand["canonical_name"],
                                domain=cand["domain"],
                                website=cand["website"],
                                metadata=metadata
                            )
                        
                        if fast_pathed:
                            # Direct crawl queue bypass
                            cursor_q = conn.execute('''
                                SELECT 1 FROM local_queues 
                                WHERE queue_name = 'crawl_queue' AND json_extract(payload, '$.company_id') = ?
                            ''', (cid,))
                            if not cursor_q.fetchone():
                                self.queue.push("crawl_queue", {"company_id": cid})
                                logger.info(f"Fast-pathed & enqueued company for crawl: {cid}")
                                processed_count += 1
                        else:
                            # Standard fallback: push to verification_queue
                            cursor_q = conn.execute('''
                                SELECT 1 FROM local_queues 
                                WHERE queue_name = 'verification_queue' AND json_extract(payload, '$.company_id') = ?
                            ''', (cid,))
                            if not cursor_q.fetchone():
                                self.queue.push("verification_queue", {"company_id": cid})
                                Telemetry.record_event(
                                    stage=Stage.VERIFICATION_QUEUED,
                                    status=Status.SUCCESS,
                                    run_id=f"enqueue-verification-{cid}-{int(time.time())}",
                                    company_id=cid,
                                    worker_name=self.worker_id,
                                    metadata={"source": "CompanyDiscoveryWorker"}
                                )
                                logger.info(f"Enqueued company for verification: {cid}")
                                processed_count += 1

                self.heartbeat(jobs_processed=processed_count)
                
                # Update metrics
                self.metrics.update_business_metric("total_discovered_companies", processed_count)
                
                time.sleep(settings.discovery_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in CompanyDiscoveryWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                time.sleep(60)

        self.stop()
        logger.info("CompanyDiscoveryWorker stopped.")

if __name__ == "__main__":
    worker = CompanyDiscoveryWorker()
    worker.run()
