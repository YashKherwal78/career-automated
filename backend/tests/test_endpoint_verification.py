import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.endpoint_verification import is_endpoint_verified


# ---------------------------------------------------------------------------
# Real-SQL tests.
#
# The mocked tests below never execute the SQL string, so they happily passed
# while the module queried `ats_registry.ats_type` -- a column migration 010
# renamed to `provider_id` years of rows ago. These tests stand up a REAL
# sqlite table with the real column names, so any future column rename fails
# loudly here instead of at runtime against the live 62k-row table.
# ---------------------------------------------------------------------------

# Trimmed to the columns this module touches, but the names must match
# src/database/migrations/002_endpoint_verification.sql as amended by
# 010_endpoint_intelligence.sql (ats_type -> provider_id).
_ATS_REGISTRY_DDL = """
CREATE TABLE ats_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT,
    company_domain TEXT,
    company_name TEXT,
    provider_id TEXT,
    endpoint TEXT,
    status TEXT,
    created_at REAL,
    last_verified REAL
)
"""


@pytest.fixture
def real_registry_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(_ATS_REGISTRY_DDL)
    conn.commit()

    @contextmanager
    def _get_connection():
        yield conn

    with patch("src.ingestion.endpoint_verification.get_connection", _get_connection), \
         patch("src.ingestion.endpoint_verification.is_postgres", return_value=False):
        yield conn
    conn.close()


def test_is_endpoint_verified_runs_against_real_ats_registry_columns(real_registry_db):
    real_registry_db.execute(
        "INSERT INTO ats_registry (company_domain, provider_id, endpoint, status) VALUES (?, ?, ?, ?)",
        ("acme.com", "workday", "https://acme.wd1.myworkdayjobs.com/careers", "VERIFIED"),
    )
    real_registry_db.commit()

    assert is_endpoint_verified("acme.com", "workday") is True


def test_is_endpoint_verified_accepts_active_lifecycle_state(real_registry_db):
    # 'ACTIVE' is what the discovery subsystem writes for a live endpoint.
    real_registry_db.execute(
        "INSERT INTO ats_registry (company_domain, provider_id, status) VALUES (?, ?, ?)",
        ("acme.com", "greenhouse", "ACTIVE"),
    )
    real_registry_db.commit()

    assert is_endpoint_verified("acme.com", "greenhouse") is True


def test_is_endpoint_verified_false_for_unverified_status(real_registry_db):
    real_registry_db.execute(
        "INSERT INTO ats_registry (company_domain, provider_id, status) VALUES (?, ?, ?)",
        ("acme.com", "lever", "DISCOVERED"),
    )
    real_registry_db.commit()

    assert is_endpoint_verified("acme.com", "lever") is False


def test_is_endpoint_verified_false_when_no_row_in_real_table(real_registry_db):
    assert is_endpoint_verified("nobody.com", "workday") is False


def test_is_endpoint_verified_does_not_match_other_provider(real_registry_db):
    real_registry_db.execute(
        "INSERT INTO ats_registry (company_domain, provider_id, status) VALUES (?, ?, ?)",
        ("acme.com", "workday", "VERIFIED"),
    )
    real_registry_db.commit()

    assert is_endpoint_verified("acme.com", "greenhouse") is False


def test_module_exposes_no_ats_registry_writer():
    """`ats_registry` is a live production table owned by the discovery
    subsystem, and on Postgres provider_id carries an FK to a seeded
    ats_providers table. The ingestion pipeline must stay read-only here."""
    import src.ingestion.endpoint_verification as ev

    assert not hasattr(ev, "mark_endpoint_verified")


# --- Mocked tests kept as a cheap smoke check of the row-shape handling ---

@patch("src.ingestion.endpoint_verification.get_connection")
def test_is_endpoint_verified_handles_tuple_rows(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = ("VERIFIED",)
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert is_endpoint_verified("acme.com", "workday") is True
