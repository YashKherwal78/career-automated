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
