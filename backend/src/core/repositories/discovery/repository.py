import json
from typing import List, Dict, Any, Optional
from src.core.repositories.base import BaseRepository

class DiscoveryRepository(BaseRepository):
    def get_checkpoint(self, worker_name: str) -> int:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            row = conn.execute(f"SELECT last_checkpoint FROM worker_progress WHERE worker_name = {p}", (worker_name,)).fetchone()
            
            if row:
                return int(row["last_checkpoint"] or 0) if isinstance(row, dict) else int(row[0] or 0)
            return 0

    def next_batch(self, last_id: int, num_shards: int, shard_id: int, limit: int) -> List[Dict[str, Any]]:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            limit_clause = conn.dialect.create_limit(limit)
            # Use modulo operator for sharding. Must use %% in the SQL string because
            # psycopg treats a bare % as a format placeholder, causing "incomplete placeholder" errors.
            # %% is the escaped literal percent sign in psycopg-formatted queries.
            cursor = conn.execute(
                f"SELECT id, company_id, canonical_name, domain, website, aliases "
                f"FROM company_identities "
                f"WHERE id > {p} AND id %% {p} = {p} "
                f"ORDER BY id ASC {limit_clause}",
                (last_id, num_shards, shard_id)
            )
            
            return [dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

    def save_candidates(self, candidates: List[Dict[str, Any]]) -> None:
        if not candidates:
            return
            
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            upsert = conn.dialect.upsert(
                table="endpoint_candidates",
                conflict_columns=["company_id", "provider_id", "url"],
                update_columns=["confidence_score"]
            )
            
            # Since update_columns only handles straightforward EXCLUDED mapping, 
            # custom expressions like times_seen + 1 need either an extended upsert
            # builder, or we write it directly if ANSI SQL DO UPDATE SET is used.
            # We can write the ANSI DO UPDATE directly since it's supported by both.
            for cand in candidates:
                evidence_str = json.dumps(cand.get("evidence", []))
                conn.execute(f'''
                    INSERT INTO endpoint_candidates (company_id, provider_id, url, discovery_source, evidence, confidence_score)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p})
                    ON CONFLICT (company_id, provider_id, url) DO UPDATE SET
                        confidence_score = EXCLUDED.confidence_score,
                        times_seen = endpoint_candidates.times_seen + 1,
                        last_seen = {now}
                ''', (cand["company_id"], cand["provider_id"], cand["url"], cand.get("discovery_source", "DiscoveryOrchestrator"), evidence_str, cand.get("confidence_score", 0)))

    def enqueue_for_verification(self, company_ids: List[str]) -> None:
        if not company_ids:
            return
        from src.discovery.pipeline_state_manager import PipelineStateManager
        with self.transaction() as conn:
            PipelineStateManager.transition_batch(
                company_ids, 
                "VERIFICATION_PENDING", 
                queue_op_name="verification_queue",
                conn=conn
            )

    def company_exists(self, domain: str) -> bool:
        if not domain:
            return True
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f"SELECT 1 FROM company_identities WHERE domain = {p} OR company_id = {p}", (domain, domain.split(".")[0]))
            return cursor.fetchone() is not None

    def persist_seed_metadata(self, company_id: str, seed: dict, domain: str, dt_str: str) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            # Check if domain or company_id already exists to prevent duplicate domain key violation
            cursor = conn.execute(f"SELECT 1 FROM company_identities WHERE company_id = {p} OR domain = {p}", (company_id, domain))
            if not cursor.fetchone():
                # 1. Insert seed to company_identities
                conn.execute(
                    f"""
                    INSERT INTO company_identities (company_id, legal_name, canonical_name, website, domain)
                    VALUES ({p}, {p}, {p}, {p}, {p})
                    ON CONFLICT (company_id) DO NOTHING
                    """,
                    (company_id, seed["name"], company_id, seed["website"], domain)
                )
            
            # 2. Insert metadata to company_discovery_sources
            cursor = conn.execute(
                f"SELECT first_seen FROM company_discovery_sources WHERE company_name = {p} AND source = {p} AND discovery_type = {p}",
                (seed["name"], seed["source"], "automated")
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    f"""
                    UPDATE company_discovery_sources
                    SET last_seen = {p}, confidence = {p}
                    WHERE company_name = {p} AND source = {p} AND discovery_type = {p}
                    """,
                    (dt_str, int(seed.get("confidence", 1.0) * 10), seed["name"], seed["source"], "automated")
                )
            else:
                conn.execute(
                    f"""
                    INSERT INTO company_discovery_sources (company_name, source, discovery_type, confidence, first_seen, last_seen)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p})
                    """,
                    (seed["name"], seed["source"], "automated", int(seed.get("confidence", 1.0) * 10), dt_str, dt_str)
                )

    def import_csv_seed(self, company_id: str, domain: str, name: str, website: str, aliases_json: str | None) -> bool:
        """Imports a single seed from CSV and returns True if a new company was inserted."""
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f"SELECT aliases FROM company_identities WHERE company_id = {p} OR domain = {p}", (company_id, domain))
            
            existing = cursor.fetchone()
            existing_aliases = existing.get("aliases") if isinstance(existing, dict) else (existing[0] if existing else None)
            
            if not existing:
                conn.execute(f'''
                    INSERT INTO company_identities (company_id, domain, canonical_name, website, aliases, lifecycle_state)
                    VALUES ({p}, {p}, {p}, {p}, {p}, NULL)
                    ON CONFLICT (company_id) DO NOTHING
                ''', (company_id, domain, name, website, aliases_json))
                return True
            elif existing and not existing_aliases and aliases_json:
                conn.execute(f'UPDATE company_identities SET aliases = {p} WHERE company_id = {p} OR domain = {p}', (aliases_json, company_id, domain))
            return False

