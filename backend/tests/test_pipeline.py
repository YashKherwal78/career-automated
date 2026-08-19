import os
import pytest
from unittest.mock import MagicMock, patch
from src.ingestion.job_lead import JobLead
import src.ingestion.pipeline as pipeline
from src.ingestion.pipeline import run_lead, EXECUTIONS_DIR


def _lead():
    return JobLead(company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
                    location="Remote", jd_excerpt=None, source="screenshot", source_ref="/tmp/x.png")


@pytest.fixture(autouse=True)
def _isolated_executions_dir(tmp_path, monkeypatch):
    """run_lead writes result.json under EXECUTIONS_DIR on every branch.
    Point that at tmp_path rather than cleaning up afterwards: a
    sweep-on-teardown fixture still leaks real directories into
    backend/executions/ whenever a test fails partway through."""
    exec_dir = tmp_path / "executions"
    exec_dir.mkdir()
    monkeypatch.setattr(pipeline, "EXECUTIONS_DIR", str(exec_dir))
    return str(exec_dir)


@pytest.fixture(autouse=True)
def _no_dedup_writes():
    """run_lead records every terminal outcome in ingested_job_leads. These
    tests are about routing/mapping, not persistence -- record_lead has its
    own real-sqlite round-trip tests in test_jd_enrichment.py."""
    with patch("src.ingestion.pipeline.record_lead") as recorder:
        yield recorder


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich_with_web_search", side_effect=lambda lead: lead)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=("google_forms", "google_forms"))
@patch("src.ingestion.pipeline.apply_to_job")
def test_run_lead_calls_apply_to_job_with_mapped_job_row(mock_apply, mock_resolve, mock_enrich, mock_web, mock_dup):
    mock_result = MagicMock(status="COMPLETED", really_submitted=False, confirmation_url="",
                             screenshot_path="", submitted_answers={}, failure_reason="")
    mock_apply.return_value = mock_result

    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)

    called_job_row = mock_apply.call_args.args[0]
    assert called_job_row["title"] == "Backend Engineer"
    assert called_job_row["canonical_name"] == "Acme"
    assert called_job_row["provider"] == "google_forms"
    assert called_job_row["apply_url"] == "https://forms.gle/abc123"
    assert called_job_row["job_id"]  # non-empty — _map_job_row reads "job_id", not "id"
    assert outcome["status"] == "COMPLETED"
    assert outcome["job_lead"]["company"] == "Acme"


@patch("src.ingestion.pipeline.already_applied", return_value=True)
def test_run_lead_skips_when_already_applied(mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    assert outcome["status"] == "SKIPPED_DUPLICATE"


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=(None, "unrecognized URL"))
def test_run_lead_returns_review_required_when_connector_unresolved(mock_resolve, mock_enrich, mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    assert outcome["status"] == "REVIEW_REQUIRED"
    assert "unrecognized URL" in outcome["failure_reason"]


def test_executions_dir_resolves_under_backend_not_repo_root():
    # Regression test: EXECUTIONS_DIR previously had one extra ".." and
    # resolved to <repo-root>/executions instead of backend/executions.
    resolved = os.path.abspath(EXECUTIONS_DIR)
    assert os.path.basename(resolved) == "executions"
    assert os.path.basename(os.path.dirname(resolved)) == "backend"


@patch("src.ingestion.pipeline.already_applied", return_value=True)
def test_run_lead_writes_result_json_under_backend_executions_for_skipped_duplicate(mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    result_path = os.path.join(pipeline.EXECUTIONS_DIR, outcome["run_id"], "result.json")
    assert os.path.isfile(result_path)
    assert os.path.abspath(result_path).startswith(os.path.abspath(pipeline.EXECUTIONS_DIR))
    assert outcome["jd_source"] == "none"


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=(None, "unrecognized URL"))
def test_run_lead_writes_result_json_under_backend_executions_for_review_required(mock_resolve, mock_enrich, mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    result_path = os.path.join(pipeline.EXECUTIONS_DIR, outcome["run_id"], "result.json")
    assert os.path.isfile(result_path)


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich_with_web_search", side_effect=lambda lead: lead)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=("google_forms", "google_forms"))
@patch("src.ingestion.pipeline.apply_to_job")
def test_run_lead_writes_result_json_under_backend_executions_for_success(mock_apply, mock_resolve, mock_enrich, mock_web, mock_dup):
    mock_result = MagicMock(status="COMPLETED", really_submitted=False, confirmation_url="",
                             screenshot_path="", submitted_answers={}, failure_reason="")
    mock_apply.return_value = mock_result

    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    result_path = os.path.join(pipeline.EXECUTIONS_DIR, outcome["run_id"], "result.json")
    assert os.path.isfile(result_path)


def test_map_job_row_passes_through_execution_dir_and_description():
    from src.applications.apply_service import _map_job_row

    mapped = _map_job_row({
        "job_id": "abc-123", "title": "Backend Engineer", "canonical_name": "Acme",
        "provider": "google_forms", "location": "Remote", "apply_url": "https://forms.gle/abc123",
        "execution_dir": "/tmp/exec/run-1", "description": "We build widgets.",
    })

    assert mapped["id"] == "abc-123"
    assert mapped["execution_dir"] == "/tmp/exec/run-1"
    assert mapped["description"] == "We build widgets."


# ---------------------------------------------------------------------------
# Dedup / audit persistence (ingested_job_leads was never written to)
# ---------------------------------------------------------------------------

@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich_with_web_search", side_effect=lambda lead: lead)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=("google_forms", "google_forms"))
@patch("src.ingestion.pipeline.apply_to_job")
def test_run_lead_records_a_successful_submission_for_dedup(mock_apply, mock_resolve, mock_enrich, mock_web, mock_dup, _no_dedup_writes):
    """already_applied() reads ingested_job_leads but nothing ever INSERTed,
    so dedup was a permanent no-op and a --live re-run of the same screenshot
    folder would resubmit every application."""
    mock_apply.return_value = MagicMock(status="COMPLETED", really_submitted=True, confirmation_url="",
                                        screenshot_path="", submitted_answers={}, failure_reason="",
                                        jd_source="form_description")

    outcome = run_lead(_lead(), user_id="user-1", test_mode=False)

    kwargs = _no_dedup_writes.call_args.kwargs
    assert kwargs["user_id"] == "user-1"
    assert kwargs["connector"] == "google_forms"
    assert kwargs["result_status"] == "COMPLETED"
    assert kwargs["really_submitted"] is True
    assert kwargs["execution_run_id"] == outcome["run_id"]
    assert kwargs["jd_source"] == "form_description"


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=(None, "unrecognized URL"))
def test_run_lead_records_an_unroutable_lead_too(mock_resolve, mock_enrich, mock_dup, _no_dedup_writes):
    run_lead(_lead(), user_id="user-1", test_mode=True)

    kwargs = _no_dedup_writes.call_args.kwargs
    assert kwargs["result_status"] == "REVIEW_REQUIRED"
    assert kwargs["really_submitted"] is False


@patch("src.ingestion.pipeline.already_applied", return_value=True)
def test_run_lead_records_skipped_duplicates_for_the_audit_trail(mock_dup, _no_dedup_writes):
    run_lead(_lead(), user_id="user-1", test_mode=True)

    assert _no_dedup_writes.call_args.kwargs["result_status"] == "SKIPPED_DUPLICATE"


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich_with_web_search", side_effect=lambda lead: lead)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=("google_forms", "google_forms"))
@patch("src.ingestion.pipeline.apply_to_job")
def test_google_forms_leads_skip_the_pipeline_level_web_search(mock_apply, mock_resolve, mock_enrich, mock_web, mock_dup, _no_dedup_writes):
    """The adapter runs steps 2 and 3 itself while the browser is already on
    the form; doing step 3 here would spend a search call step 2 usually
    makes unnecessary."""
    mock_apply.return_value = MagicMock(status="COMPLETED", really_submitted=False, confirmation_url="",
                                        screenshot_path="", submitted_answers={}, failure_reason="",
                                        jd_source="web_search")

    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)

    mock_web.assert_not_called()
    # ...and the adapter's own accounting wins, since it knows which step fired.
    assert outcome["jd_source"] == "web_search"
