"""Read-only lookups against the shared `ats_registry` table.

This module deliberately contains NO writers. `ats_registry` is a live,
production-sized table (62,705 rows at the time of writing) that is owned by
the discovery/bootstrap subsystem (`src/core/repositories/company/metadata.py`,
`src/bootstrap/import_company_datasets.py`). On Postgres it also carries a
foreign key from `ats_registry.provider_id` to the seeded `ats_providers`
table, so inserting a row for a provider the seed doesn't know about raises an
integrity error mid-run. The ingestion pipeline therefore only *reads* here;
see routing.resolve_connector for what happens when an endpoint isn't known.

Note the column name: migration 010 renamed `ats_registry.ats_type` to
`provider_id`. The parameter is still called `ats_type` for callers, but every
SQL statement must reference `provider_id`.
"""
from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres

logger = setup_logger("endpoint_verification")

# Lifecycle states (endpoint_lifecycle_enum, migration 010) that mean "we have
# actually confirmed this endpoint works". 'ACTIVE' is what the discovery
# subsystem writes for a live, crawled endpoint; 'VERIFIED' is the state an
# explicit verification pass sets. Both count as verified for routing.
_VERIFIED_STATUSES = ("VERIFIED", "ACTIVE")


def is_endpoint_verified(company_domain: str, ats_type: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT status FROM ats_registry WHERE company_domain = {ph} AND provider_id = {ph}",
            (company_domain, ats_type),
        )
        row = cur.fetchone()
        if not row:
            return False
        status = row["status"] if hasattr(row, "keys") else row[0]
        return str(status).upper() in _VERIFIED_STATUSES
