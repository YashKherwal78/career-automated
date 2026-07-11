import sqlite3
import json
import hashlib
import time
import logging
import datetime
from typing import List, Dict, Any, Tuple, TypedDict, Optional

logger = logging.getLogger("company_orchestrator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
if not logger.handlers:
    logger.addHandler(handler)

class Company(TypedDict):
    """
    The immutable schema consumed by the rest of the Job Machine.
    The downstream engines will never know if this data came from YC, Kaggle, GitHub, or LinkedIn.
    """
    id: str
    name: str
    website: str
    description: Optional[str]
    yc_batch: Optional[str]
    industries: List[str]
    tags: List[str]
    location: Optional[str]
    founders: List[str]
    hiring_signal: Optional[str]
    funding_signal: Optional[str]
    source_metadata: Dict[str, Any]

class CompanySource:
    priority: int = 0
    name: str = "Unknown"
    supports_etag: bool = False
    supports_incremental: bool = False
    supports_streaming: bool = False
    
    def fetch_companies(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

class SourceOrchestrator:
    NORMALIZATION_VERSION = 1
    
    def __init__(self, db_path: str, config: dict = None, dry_run: bool = False):
        self.db_path = db_path
        self.config = config or {}
        self.dry_run = dry_run
        self._init_db()
        self.sources: List[CompanySource] = []
        self.metrics = {
            "total_discovered": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "duplicates_merged": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "runtime_ms": 0,
            "retries": 0,
            "failures": 0
        }

    def _init_db(self):
        if self.dry_run: return
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS connector_cache (
                source TEXT PRIMARY KEY,
                raw_json TEXT,
                last_updated TEXT,
                etag TEXT,
                checksum TEXT,
                normalization_version INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS company_cache (
                company_id TEXT PRIMARY KEY,
                json TEXT,
                last_updated TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS source_health (
                source_name TEXT PRIMARY KEY,
                last_success TEXT,
                last_failure TEXT,
                consecutive_failures INTEGER DEFAULT 0,
                avg_latency REAL DEFAULT 0.0
            )
        ''')
        conn.commit()
        conn.close()

    def add_source(self, source: CompanySource):
        self.sources.append(source)
        if not self.dry_run:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO source_health (source_name) VALUES (?)", (source.name,))
            conn.commit()
            conn.close()

    def _update_health(self, source_name: str, success: bool, latency: float):
        if self.dry_run: return
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if success:
            c.execute('''
                UPDATE source_health 
                SET last_success = CURRENT_TIMESTAMP, consecutive_failures = 0, 
                    avg_latency = (avg_latency + ?) / 2.0
                WHERE source_name = ?
            ''', (latency, source_name))
        else:
            c.execute('''
                UPDATE source_health 
                SET last_failure = CURRENT_TIMESTAMP, consecutive_failures = consecutive_failures + 1 
                WHERE source_name = ?
            ''', (source_name,))
        conn.commit()
        conn.close()

    def _should_skip_source(self, source_name: str) -> bool:
        if self.dry_run: return False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT consecutive_failures FROM source_health WHERE source_name = ?", (source_name,))
        row = c.fetchone()
        conn.close()
        return row and row[0] >= 3

    def _parse_ttl(self, ttl_str: str) -> int:
        if ttl_str.endswith('h'): return int(ttl_str[:-1])
        if ttl_str.endswith('d'): return int(ttl_str[:-1]) * 24
        return 24

    def _is_cache_fresh(self, source_name: str) -> bool:
        if self.dry_run: return False
        ttl_map = self.config.get("yc_orchestrator", {}).get("ttl", {})
        ttl_hours = self._parse_ttl(ttl_map.get(source_name, "24h"))
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(f'''
            SELECT 1 FROM connector_cache 
            WHERE source = ? AND normalization_version = ? AND last_updated > datetime('now', '-{ttl_hours} hours')
            LIMIT 1
        ''', (source_name, self.NORMALIZATION_VERSION))
        is_fresh = c.fetchone() is not None
        conn.close()
        return is_fresh

    def fetch_companies(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        start_time = time.time()
        self.sources.sort(key=lambda s: s.priority, reverse=True)
        
        merged_output = []
        for source in self.sources:
            if self._should_skip_source(source.name):
                logger.warning(f"Skipping {source.name} due to health.")
                self.metrics["skipped"] += 1
                continue
                
            if self._is_cache_fresh(source.name):
                logger.info(f"Cache hit for {source.name}. Using raw cache.")
                self.metrics["cache_hits"] += 1
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("SELECT raw_json FROM connector_cache WHERE source = ?", (source.name,))
                companies = json.loads(c.fetchone()[0])
                conn.close()
                merged_output = self._merge_companies(companies, source, merged_output)
                continue
                
            logger.info(f"Attempting network source: {source.name} (Priority {source.priority})")
            t0 = time.time()
            try:
                companies = source.fetch_companies()
                latency = time.time() - t0
                if companies:
                    self._update_health(source.name, True, latency)
                    self.metrics["cache_misses"] += 1
                    
                    if not self.dry_run:
                        conn = sqlite3.connect(self.db_path)
                        c = conn.cursor()
                        c.execute('''
                            INSERT OR REPLACE INTO connector_cache (source, raw_json, last_updated, normalization_version)
                            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
                        ''', (source.name, json.dumps(companies), self.NORMALIZATION_VERSION))
                        conn.commit()
                        conn.close()
                        
                    merged_output = self._merge_companies(companies, source, merged_output)
                else:
                    self._update_health(source.name, False, latency)
            except Exception as e:
                latency = time.time() - t0
                self._update_health(source.name, False, latency)
                self.metrics["failures"] += 1
                logger.error(f"Source {source.name} failed: {e}")
                
        self.metrics["runtime_ms"] = int((time.time() - start_time) * 1000)
        return merged_output, self.metrics

    def _generate_id(self, name: str, website: str) -> str:
        name = str(name).strip().lower()
        website = str(website).strip().lower()
        return hashlib.sha256(f"{name}|{website}".encode()).hexdigest()

    def _merge_companies(self, companies: List[Dict[str, Any]], source: CompanySource, current_merged: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        conn = None
        c = None
        if not self.dry_run:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
        current_map = {comp.get("company_id"): comp for comp in current_merged}
        now = datetime.datetime.now().isoformat()
        
        for raw_comp in companies:
            self.metrics["total_discovered"] += 1
            cid = self._generate_id(raw_comp.get("name", ""), raw_comp.get("website", ""))
            
            # Fetch from DB cache if available and not already in memory
            cached = None
            if cid in current_map:
                cached = current_map[cid]
                self.metrics["duplicates_merged"] += 1
            elif not self.dry_run:
                c.execute("SELECT json FROM company_cache WHERE company_id = ?", (cid,))
                row = c.fetchone()
                if row:
                    cached = json.loads(row[0])
                    
            if not cached:
                self.metrics["inserted"] += 1
                cached = {"company_id": cid}
                
            is_updated = False
            for k, v in raw_comp.items():
                if not v: continue
                # Field-level provenance check
                existing_field = cached.get(k, {})
                existing_priority = existing_field.get("priority", -1) if isinstance(existing_field, dict) else -1
                
                if source.priority >= existing_priority:
                    # Overwrite or fill missing
                    if existing_priority != -1 and existing_priority == source.priority and existing_field.get("value") == v:
                        continue # No change
                        
                    cached[k] = {
                        "value": v,
                        "source": source.name,
                        "priority": source.priority,
                        "updated_at": now
                    }
                    is_updated = True

            if is_updated and cid in current_map:
                self.metrics["updated"] += 1
                
            current_map[cid] = cached
            
            if not self.dry_run and is_updated:
                c.execute('''
                    INSERT OR REPLACE INTO company_cache (company_id, json, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (cid, json.dumps(cached)))
                
        if not self.dry_run:
            conn.commit()
            conn.close()
            
        return list(current_map.values())
