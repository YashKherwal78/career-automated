from unittest.mock import MagicMock, patch, AsyncMock
from src.ingestion.job_lead import JobLead
from src.ingestion.jd_enrichment import enrich, already_applied, enrich_with_web_search


def _lead(**overrides):
    base = dict(company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
                location=None, jd_excerpt=None, source="screenshot", source_ref="/tmp/x.png")
    base.update(overrides)
    return JobLead(**base)


def test_enrich_fills_jd_from_internal_db_match():
    lead = _lead(jd_excerpt=None)
    mock_repos = MagicMock()
    mock_repos.job.get_jobs.return_value = [
        {"title": "Backend Engineer", "canonical_name": "Acme", "description": "We build widgets."}
    ]

    enriched = enrich(lead, repos=mock_repos)

    assert enriched.jd_excerpt == "We build widgets."
    mock_repos.job.get_jobs.assert_called_once()


def test_enrich_leaves_existing_jd_untouched():
    lead = _lead(jd_excerpt="Already have one.")
    mock_repos = MagicMock()

    enriched = enrich(lead, repos=mock_repos)

    assert enriched.jd_excerpt == "Already have one."
    mock_repos.job.get_jobs.assert_not_called()


def test_enrich_returns_lead_unchanged_when_no_db_match():
    lead = _lead(jd_excerpt=None)
    mock_repos = MagicMock()
    mock_repos.job.get_jobs.return_value = []

    enriched = enrich(lead, repos=mock_repos)

    assert enriched.jd_excerpt is None


@patch("src.ingestion.jd_enrichment.get_connection")
def test_already_applied_true_when_row_exists(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"id": "abc"}
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert already_applied(_lead(), user_id="user-1") is True


@patch("src.ingestion.jd_enrichment.get_connection")
def test_already_applied_false_when_no_row(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert already_applied(_lead(), user_id="user-1") is False


@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_fills_jd_from_first_result(mock_backend_cls):
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=["https://acme.com/careers/backend-engineer"])

    lead = _lead(jd_excerpt=None)
    enriched = enrich_with_web_search(lead)

    assert enriched.apply_link == lead.apply_link  # unchanged
    mock_backend.search.assert_called_once_with("Acme Backend Engineer job description")


@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_leaves_lead_unchanged_on_no_results(mock_backend_cls):
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=[])

    lead = _lead(jd_excerpt=None)
    enriched = enrich_with_web_search(lead)

    assert enriched.jd_excerpt is None


# ---------------------------------------------------------------------------
# Web-search fallback must produce REAL job description text
# ---------------------------------------------------------------------------

@patch("src.ingestion.jd_enrichment.httpx.get")
@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_extracts_visible_page_text(mock_backend_cls, mock_http_get):
    """The excerpt used to be the literal string "(found via web search: <url>)".
    jd_excerpt is fed to QuestionEngine as prose context, so that handed the
    LLM a URL-shaped sentence and told it that was the job description."""
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=["https://acme.com/careers/backend-engineer"])
    mock_http_get.return_value = MagicMock(
        status_code=200,
        text="<html><head><style>.x{}</style></head><body><script>junk()</script>"
             "<h1>Backend Engineer</h1><p>You will build widgets in Python.</p></body></html>",
    )

    enriched = enrich_with_web_search(_lead(jd_excerpt=None))

    assert "You will build widgets in Python." in enriched.jd_excerpt
    assert "Backend Engineer" in enriched.jd_excerpt
    assert "junk()" not in enriched.jd_excerpt and ".x{}" not in enriched.jd_excerpt
    assert "found via web search" not in enriched.jd_excerpt


@patch("src.ingestion.jd_enrichment.httpx.get")
@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_leaves_jd_empty_when_page_cannot_be_fetched(mock_backend_cls, mock_http_get):
    """"No JD" must stay honestly representable as empty rather than as a
    plausible-looking placeholder the LLM would treat as prose."""
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=["https://acme.com/careers/backend-engineer"])
    mock_http_get.return_value = MagicMock(status_code=404, text="")

    assert enrich_with_web_search(_lead(jd_excerpt=None)).jd_excerpt is None


@patch("src.ingestion.jd_enrichment.httpx.get", side_effect=RuntimeError("connection reset"))
@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_survives_a_fetch_exception(mock_backend_cls, mock_http_get):
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=["https://acme.com/careers/backend-engineer"])

    assert enrich_with_web_search(_lead(jd_excerpt=None)).jd_excerpt is None


# ---------------------------------------------------------------------------
# record_lead / already_applied round trip -- the actual dedup mechanism
# ---------------------------------------------------------------------------

import sqlite3
from contextlib import contextmanager

import pytest

from src.ingestion.jd_enrichment import record_lead

_LEADS_DDL = """
CREATE TABLE ingested_job_leads (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    apply_link TEXT NOT NULL,
    source TEXT NOT NULL,
    source_ref TEXT,
    connector TEXT,
    jd_source TEXT,
    result_status TEXT,
    really_submitted INTEGER DEFAULT 0,
    execution_run_id TEXT,
    created_at REAL NOT NULL
)
"""


@pytest.fixture
def leads_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(_LEADS_DDL)
    conn.commit()

    @contextmanager
    def _get_connection():
        yield conn

    with patch("src.ingestion.jd_enrichment.get_connection", _get_connection), \
         patch("src.ingestion.jd_enrichment.is_postgres", return_value=False):
        yield conn
    conn.close()


def test_record_lead_then_already_applied_dedupes_a_real_submission(leads_db):
    """Nothing ever INSERTed into ingested_job_leads, so already_applied()
    always returned False and a --live re-run of the same screenshot folder
    would resubmit every application."""
    lead = _lead()
    assert already_applied(lead, user_id="user-1") is False

    record_lead(lead, user_id="user-1", connector="google_forms", jd_source="db_match",
                result_status="COMPLETED", really_submitted=True, execution_run_id="leads_screenshot_abc")

    assert already_applied(lead, user_id="user-1") is True


def test_record_lead_persists_every_audit_column(leads_db):
    record_lead(_lead(), user_id="user-1", connector="google_forms", jd_source="form_description",
                result_status="REVIEW_REQUIRED", really_submitted=False, execution_run_id="leads_screenshot_xyz")

    row = leads_db.execute("SELECT * FROM ingested_job_leads").fetchone()
    assert row["company"] == "Acme"
    assert row["role"] == "Backend Engineer"
    assert row["apply_link"] == "https://forms.gle/abc123"
    assert row["source"] == "screenshot"
    assert row["source_ref"] == "/tmp/x.png"
    assert row["connector"] == "google_forms"
    assert row["jd_source"] == "form_description"
    assert row["result_status"] == "REVIEW_REQUIRED"
    assert row["really_submitted"] == 0
    assert row["execution_run_id"] == "leads_screenshot_xyz"
    assert row["id"] and row["created_at"]


def test_a_non_submitted_attempt_does_not_block_a_retry(leads_db):
    """REVIEW_REQUIRED means a human still has to finish it -- recording it
    for audit must not make the lead look already-applied."""
    lead = _lead()
    record_lead(lead, user_id="user-1", connector="google_forms", jd_source="none",
                result_status="REVIEW_REQUIRED", really_submitted=False, execution_run_id="r1")

    assert already_applied(lead, user_id="user-1") is False


def test_record_lead_never_raises_when_the_write_fails():
    """A dedup/audit write failing must not take down a run that already
    reached a terminal state."""
    with patch("src.ingestion.jd_enrichment.get_connection", side_effect=RuntimeError("db down")):
        record_lead(_lead(), user_id="user-1", connector="google_forms", jd_source="none",
                    result_status="COMPLETED", really_submitted=True, execution_run_id="r1")
