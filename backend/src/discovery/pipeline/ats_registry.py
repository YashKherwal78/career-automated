import sqlite3
import time
import logging
import json
from typing import Optional, Dict, Any, List

from src.config.config import Config
from src.discovery.registry.ats_providers import VerificationResult

logger = logging.getLogger("ATSRegistry")

class ATSRegistry:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ats_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT,
                    company_domain TEXT,
                    company_name TEXT,
                    ats_type TEXT,
                    endpoint TEXT,
                    canonical_endpoint TEXT,
                    endpoint_hash TEXT,
                    status TEXT,
                    discovery_source TEXT,
                    search_provider TEXT,
                    search_query TEXT,
                    search_rank INTEGER,
                    identity_score REAL,
                    inspector_score REAL,
                    plugin_name TEXT,
                    plugin_version TEXT,
                    ats_metadata TEXT,
                    created_at REAL,
                    last_checked REAL,
                    last_verified REAL,
                    recheck_after REAL,
                    retired_at REAL,
                    last_job_sync REAL,
                    last_successful_crawl REAL,
                    crawl_status TEXT,
                    job_count INTEGER
                )
            """)
            
            # Create indices if they don't exist
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_active_company ON ats_registry(company_id, status) WHERE status='ACTIVE'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_registry_endpoint_hash ON ats_registry(endpoint_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_registry_company_id ON ats_registry(company_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_registry_status ON ats_registry(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_registry_ats_type ON ats_registry(ats_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_registry_recheck_after ON ats_registry(recheck_after)")
            conn.commit()

    def get_active_endpoint(self, company_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM ats_registry WHERE company_id = ? AND status = 'ACTIVE'", (company_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def record_health_check(self, endpoint_id: int, status: str, next_recheck_timestamp: float):
        with sqlite3.connect(self.db_path) as conn:
            now = time.time()
            if status == 'ACTIVE':
                conn.execute("""
                    UPDATE ats_registry 
                    SET status = ?, last_checked = ?, last_verified = ?, recheck_after = ?
                    WHERE id = ?
                """, (status, now, now, next_recheck_timestamp, endpoint_id))
            else:
                conn.execute("""
                    UPDATE ats_registry 
                    SET status = ?, last_checked = ?, recheck_after = ?
                    WHERE id = ?
                """, (status, now, next_recheck_timestamp, endpoint_id))
            conn.commit()

    def promote_endpoint(self, company_id: str, new_result: VerificationResult, connection: Optional[sqlite3.Connection] = None):
        """
        Promotes a VerificationResult to ACTIVE status.
        Compares endpoint_hash to avoid churn.
        Retires the old endpoint if it's different and the new one is better or equal.
        """
        import hashlib
        from urllib.parse import urlparse
        
        endpoint_hash = hashlib.sha256(new_result.canonical_endpoint.encode()).hexdigest()
        parsed = urlparse(new_result.endpoint if new_result.endpoint.startswith('http') else f"https://{new_result.endpoint}")
        company_domain = parsed.netloc.replace('www.', '')

        def _execute_promotion(conn):
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM ats_registry WHERE company_id = ? AND status != 'RETIRED' ORDER BY created_at DESC LIMIT 1", (company_id,))
            existing = cursor.fetchone()

            now = time.time()
            
            # Avoid churn
            if existing and existing['endpoint_hash'] == endpoint_hash:
                # Same endpoint, just update timestamps
                conn.execute("""
                    UPDATE ats_registry 
                    SET last_checked = ?, last_verified = ?, recheck_after = ?, status = 'ACTIVE'
                    WHERE id = ?
                """, (now, now, now + 14 * 24 * 3600, existing['id']))
                return

            # Asserts new confidence is >= existing
            new_confidence = getattr(new_result, 'confidence', getattr(new_result, 'identity_score', 0.0))
            if existing and new_confidence < existing['identity_score']:
                logger.warning(f"Rejecting promotion for {company_id}: new score {new_confidence} < existing {existing['identity_score']}")
                return

            provider = getattr(new_result, 'provider', getattr(new_result, 'ats_type', 'Unknown'))
            identity_score = getattr(new_result, 'identity_score', new_confidence)
            inspector_score = getattr(new_result, 'inspector_score', 0.0)
            plugin_name = getattr(new_result, 'plugin_name', '')
            plugin_version = getattr(new_result, 'plugin_version', '1.0')
            
            raw_metadata = getattr(new_result, 'metadata', getattr(new_result, 'ats_metadata', '{}'))
            ats_metadata = raw_metadata if isinstance(raw_metadata, str) else json.dumps(raw_metadata)

            # Retire existing endpoint BEFORE new one is inserted to satisfy the UNIQUE index
            from src.api.db import is_postgres
            if existing:
                if is_postgres():
                    conn.execute("""
                        UPDATE ats_registry 
                        SET status = 'RETIRED', retired_at = %s
                        WHERE id = %s
                    """, (now, existing['id']))
                else:
                    conn.execute("""
                        UPDATE ats_registry 
                        SET status = 'RETIRED', retired_at = ?
                        WHERE id = ?
                    """, (now, existing['id']))

            # Insert new ACTIVE endpoint
            if is_postgres():
                conn.execute("""
                    INSERT INTO ats_registry (
                        company_id, company_domain, company_name, ats_type, endpoint, canonical_endpoint, endpoint_hash,
                        status, discovery_source, search_provider, search_query, search_rank,
                        identity_score, inspector_score, plugin_name, plugin_version, ats_metadata,
                        created_at, last_checked, last_verified, recheck_after
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_result.company_id,
                    company_domain,
                    new_result.company_name,
                    provider,
                    new_result.endpoint,
                    new_result.canonical_endpoint,
                    endpoint_hash,
                    'ACTIVE',
                    getattr(new_result, 'discovery_source', 'ValidationEngine'),
                    getattr(new_result, 'search_provider', None),
                    getattr(new_result, 'search_query', None),
                    getattr(new_result, 'search_rank', None),
                    identity_score,
                    inspector_score,
                    plugin_name,
                    plugin_version,
                    ats_metadata,
                    now, now, now, now + 14 * 24 * 3600
                ))
            else:
                conn.execute("""
                    INSERT INTO ats_registry (
                        company_id, company_domain, company_name, ats_type, endpoint, canonical_endpoint, endpoint_hash,
                        status, discovery_source, search_provider, search_query, search_rank,
                        identity_score, inspector_score, plugin_name, plugin_version, ats_metadata,
                        created_at, last_checked, last_verified, recheck_after
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_result.company_id,
                    company_domain,
                    new_result.company_name,
                    provider,
                    new_result.endpoint,
                    new_result.canonical_endpoint,
                    endpoint_hash,
                    'ACTIVE',
                    getattr(new_result, 'discovery_source', 'ValidationEngine'),
                    getattr(new_result, 'search_provider', None),
                    getattr(new_result, 'search_query', None),
                    getattr(new_result, 'search_rank', None),
                    identity_score,
                    inspector_score,
                    plugin_name,
                    plugin_version,
                    ats_metadata,
                    now, now, now, now + 14 * 24 * 3600
                ))

        if connection:
            _execute_promotion(connection)
        else:
            from src.api.db import is_postgres, get_connection
            with sqlite3.connect(self.db_path) if not is_postgres() else get_connection() as conn:
                _execute_promotion(conn)
                conn.commit()

    def snapshot_registry(self, snapshot_name: str):
        """For regression safety: creates a backup of the current ats_registry table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS snapshot_{snapshot_name} AS SELECT * FROM ats_registry")
            conn.commit()
