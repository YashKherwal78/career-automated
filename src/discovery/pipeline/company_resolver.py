"""
Pipeline B — Company Resolver.

Resolves a free-text company name + apply URL from a job board listing into a
company_id that matches company_identities in the database.

IMPORTANT: This class NEVER inserts into company_identities.
Pipeline A is the single authority for creating and enriching company records.
When a company cannot be resolved, this resolver enqueues the domain into
discovery_queue so Pipeline A can discover, verify, and register the company.
"""

import hashlib
import logging
import sqlite3
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("CompanyResolver")


def _extract_domain(url: str) -> str:
    """Extract bare domain from any URL, stripping www."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]          # strip port
        if host.startswith("www."):
            host = host[4:]
        return host.lower().strip()
    except Exception:
        return ""


def _domain_slug(domain: str) -> str:
    """Stable, collision-resistant company_id from a domain."""
    return "pb_" + hashlib.md5(domain.encode()).hexdigest()[:12]


class CompanyResolver:
    """
    Resolves StandardJob.company + apply_url to an existing company_id.

    Resolution priority:
      1. Exact canonical_name match in company_identities (case-insensitive).
      2. Domain match: extract domain from apply_url, match company_identities.domain.
      3. Alias match: company_identities.aliases JSON field contains the name.

    If no match is found:
      - Enqueue the domain into discovery_queue so Pipeline A can handle it.
      - Return a provisional company_id (pb_<md5 of domain>) for use in
        normalized_jobs only. This provisional id is NOT inserted into
        company_identities — Pipeline A will create the authoritative record
        when it processes the discovery_queue entry.
    """

    def __init__(self, db_path: str, queue):
        """
        Args:
            db_path: Path to the SQLite database.
            queue:   A SQLiteQueue instance (from BaseWorker.queue) used to
                     enqueue unknown companies into discovery_queue.
        """
        self.db_path = db_path
        self.queue = queue

    def resolve(self, company_name: str, apply_url: str) -> str:
        """
        Resolve company_name + apply_url to a company_id.

        Returns:
            str: An existing company_id from company_identities, or a
                 provisional "pb_<hash>" id if the company is unknown.
                 Unknown companies are enqueued into discovery_queue.
        """
        domain = _extract_domain(apply_url)

        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Exact canonical_name match (case-insensitive)
            row = conn.execute(
                "SELECT company_id FROM company_identities WHERE LOWER(canonical_name) = ?",
                (company_name.lower().strip(),)
            ).fetchone()
            if row:
                return row["company_id"]

            # 2. Domain match from apply_url
            if domain:
                row = conn.execute(
                    "SELECT company_id FROM company_identities WHERE domain = ?",
                    (domain,)
                ).fetchone()
                if row:
                    return row["company_id"]

            # 3. Alias match (aliases stored as JSON array in company_identities)
            if company_name:
                rows = conn.execute(
                    "SELECT company_id, aliases FROM company_identities WHERE aliases IS NOT NULL"
                ).fetchall()
                name_lower = company_name.lower().strip()
                for r in rows:
                    try:
                        import json
                        aliases = json.loads(r["aliases"]) or []
                        if name_lower in [a.lower() for a in aliases]:
                            return r["company_id"]
                    except Exception:
                        continue

        # No match found — enqueue domain into discovery_queue for Pipeline A.
        # Pipeline A will create the authoritative company record.
        if domain:
            self._enqueue_for_pipeline_a(company_name, domain, apply_url)

        # Return provisional id. This is used only as a company_id in
        # normalized_jobs until Pipeline A resolves the real identity.
        return _domain_slug(domain) if domain else _domain_slug(company_name)

    def _enqueue_for_pipeline_a(self, company_name: str, domain: str, apply_url: str):
        """
        Push a discovery payload into discovery_queue so Pipeline A will
        detect the ATS, verify endpoints, and create a company_identities record.

        Does NOT insert into company_identities — that is Pipeline A's job.
        """
        try:
            # Check if already queued to avoid duplicates
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                existing = conn.execute(
                    """SELECT 1 FROM local_queues
                       WHERE queue_name = 'discovery_queue'
                         AND json_extract(payload, '$.domain') = ?""",
                    (domain,)
                ).fetchone()

                if existing:
                    return  # Already in queue

            self.queue.push("discovery_queue", {
                "domain": domain,
                "company_name": company_name,
                "website": f"https://{domain}",
                "source": "pipeline_b",
                "apply_url": apply_url,
            })
            logger.info(
                f"CompanyResolver: unknown company '{company_name}' ({domain}) "
                f"enqueued into discovery_queue for Pipeline A."
            )
        except Exception as e:
            logger.warning(f"CompanyResolver: failed to enqueue {domain}: {e}")
