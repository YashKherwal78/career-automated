import glob
import os
import shutil
import pytest
from unittest.mock import MagicMock, patch
from src.ingestion.job_lead import JobLead
from src.ingestion.pipeline import run_lead, EXECUTIONS_DIR


def _lead():
    return JobLead(company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
                    location="Remote", jd_excerpt=None, source="screenshot", source_ref="/tmp/x.png")


@pytest.fixture(autouse=True)
def _cleanup_execution_dirs():
    # run_lead now writes result.json under EXECUTIONS_DIR on every branch
    # (success, SKIPPED_DUPLICATE, REVIEW_REQUIRED) -- sweep up whatever this
    # test run created so the test suite doesn't litter backend/executions/.
    before = set(glob.glob(os.path.join(EXECUTIONS_DIR, "leads_screenshot_*")))
    yield
    after = set(glob.glob(os.path.join(EXECUTIONS_DIR, "leads_screenshot_*")))
    for created_dir in after - before:
        shutil.rmtree(created_dir, ignore_errors=True)


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
    result_path = os.path.join(EXECUTIONS_DIR, outcome["run_id"], "result.json")
    assert os.path.isfile(result_path)
    assert os.path.abspath(result_path).startswith(os.path.abspath(EXECUTIONS_DIR))
    assert outcome["jd_source"] == "none"


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=(None, "unrecognized URL"))
def test_run_lead_writes_result_json_under_backend_executions_for_review_required(mock_resolve, mock_enrich, mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    result_path = os.path.join(EXECUTIONS_DIR, outcome["run_id"], "result.json")
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
    result_path = os.path.join(EXECUTIONS_DIR, outcome["run_id"], "result.json")
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
