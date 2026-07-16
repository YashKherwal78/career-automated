import os
from typing import Optional, Dict, Any, List
from src.core.repositories.interfaces import ICompanyRepository
from src.core.repositories.base import BaseRepository
from src.core.repositories.registry_resolver import RegistryResolver

class CompanyRepository(BaseRepository, ICompanyRepository):
    def get_company(self, provider: str, company_id: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            table_name = RegistryResolver.metadata_table(provider)
            p = conn.dialect.placeholder()
            cur = conn.execute(f"SELECT * FROM {table_name} WHERE company_id = {p}", (company_id,))
            row = cur.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
            return None

    def get_active_company(self, company_id: str, tx=None) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cur = conn.execute(f"SELECT * FROM ats_registry WHERE company_id = {p} AND status = 'ACTIVE'", (company_id,))
            row = cur.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
            return None

    def ensure_company_identity(self, company_id: str, domain: str, canonical_name: str, website: str, tx=None) -> str:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            row = conn.execute(
                f"SELECT company_id FROM company_identities WHERE company_id = {p} OR domain = {p} OR canonical_name = {p}",
                (company_id, domain, canonical_name)
            ).fetchone()
            
            if row:
                return row["company_id"] if isinstance(row, dict) else row[0]
                
            upsert = conn.dialect.upsert(
                table="company_identities",
                conflict_columns=["company_id"],
                update_columns=[]
            )
            # When update_columns is empty, we just do DO NOTHING, but upsert builder may generate DO UPDATE SET id=id
            # A cleaner way is just ON CONFLICT DO NOTHING. We can write the ANSI SQL DO NOTHING directly,
            # as modern SQLite and Postgres both support it.
            conn.execute(
                f"INSERT INTO company_identities (company_id, domain, canonical_name, website) VALUES ({p}, {p}, {p}, {p}) ON CONFLICT (company_id) DO NOTHING",
                (company_id, domain, canonical_name or company_id, website or domain)
            )
            return company_id

    def get_company_without_active_endpoint(self, tx=None) -> Optional[str]:
        with self.transaction() as conn:
            limit = conn.dialect.create_limit(1)
            cursor = conn.execute(f'''
                SELECT i.company_id 
                FROM company_identities i
                LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
                WHERE r.company_id IS NULL
                {limit}
            ''')
            row = cursor.fetchone()
            if row:
                return row["company_id"] if isinstance(row, dict) else row[0]
            return None

    def get_company_info(self, company_id: str, tx=None) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f"SELECT canonical_name, website, domain FROM company_identities WHERE company_id = {p}", (company_id,))
            row = cursor.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cursor.description], row))
            return None

    def report_canonical_endpoint(self, company_id: str, provider_id: str, candidate_id: str, endpoint: str, canonical_endpoint: str, tx=None) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            exists = conn.execute(f"SELECT 1 FROM ats_registry WHERE company_id={p} AND provider_id={p}", (company_id, provider_id)).fetchone()
            if not exists:
                conn.execute(
                    f'''
                    INSERT INTO ats_registry (company_id, provider_id, candidate_id, endpoint, canonical_endpoint, status)
                    VALUES ({p}, {p}, {p}, {p}, {p}, 'ACTIVE')
                    ''',
                    (company_id, provider_id, candidate_id, endpoint, canonical_endpoint)
                )

    def get_companies(self, page: int=1, page_size: int=50, tx=None) -> List[Dict[str, Any]]:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            limit_clause = f"LIMIT {p} OFFSET {p}" # Standard for both dialects
            
            query = f"""
                SELECT 
                    i.company_id, 
                    i.canonical_name as company_name, 
                    i.website, 
                    r.ats_type, 
                    r.status,
                    r.job_count, 
                    r.last_checked, 
                    r.crawl_status
                FROM company_identities i
                LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
                {limit_clause}
            """
                
            cursor = conn.execute(query, (page_size, (page - 1) * page_size))
            return [dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

