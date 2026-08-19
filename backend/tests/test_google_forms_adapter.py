"""End-to-end wiring of the JD-enrichment chain through GoogleFormsAdapter.

The three steps in the spec (internal DB match -> the form's own description
-> web search) each existed but none of them were connected:
read_form_description() had no caller anywhere in the codebase, the ingestion
pipeline skipped the web-search fallback for google_forms leads assuming the
form description covered it, and even a successful DB match died here because
the adapter only read job["company_context"] -- a key nothing sets -- instead
of job["description"], which is what the pipeline populates.

These tests use a REAL GoogleFormsHandler (only its page and execute() are
faked) so the assertion "the JD actually reaches QuestionEngine" is about the
real object graph, not a mock's call args.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.applications.adapters.google_forms_adapter import GoogleFormsAdapter
from src.applications.handlers.google_forms import GoogleFormsHandler


def _job(**overrides):
    job = {
        "id": "job-1",
        "job_title": "Backend Engineer",
        "company_name": "Acme",
        "location": "Remote",
        "apply_url": "https://forms.gle/abc123",
        "execution_dir": "",
        "description": "",
    }
    job.update(overrides)
    return job


def _handler(page):
    return GoogleFormsHandler(
        page=page, job_title="Backend Engineer", company_name="Acme", location="Remote",
        resume_path="/tmp/resume.pdf", test_mode=True, execution_dir="/tmp/exec",
        profile_manager=MagicMock(), rag_client=MagicMock(), llm_client=MagicMock(),
        company_context="",
    )


def _page_with_heading(text):
    page = MagicMock()
    page.locator.return_value.first.text_content.return_value = text
    return page


# ---------------------------------------------------------------------------
# jd_source transitions through the real chain
# ---------------------------------------------------------------------------

def test_jd_source_is_none_when_no_step_yields_anything():
    adapter = GoogleFormsAdapter()
    handler = _handler(_page_with_heading(""))

    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search",
               side_effect=lambda lead: lead) as web:
        jd, source = adapter.resolve_jd(_job(), handler)

    assert (jd, source) == ("", "none")
    web.assert_called_once()


def test_jd_source_is_db_match_when_the_pipeline_supplied_a_description():
    """pipeline.py sets job_row["description"] from the internal DB match and
    _map_job_row passes it through -- the adapter never read it."""
    adapter = GoogleFormsAdapter()
    handler = _handler(_page_with_heading("Some form heading"))

    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search") as web:
        jd, source = adapter.resolve_jd(_job(description="We build widgets in Python."), handler)

    assert source == "db_match"
    assert jd == "We build widgets in Python."
    # An earlier step succeeded -- no extra (paid/rate-limited) search call.
    web.assert_not_called()


def test_jd_source_is_form_description_when_the_db_had_no_match():
    adapter = GoogleFormsAdapter()
    handler = _handler(_page_with_heading("  Join Acme as a Backend Engineer  "))

    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search") as web:
        jd, source = adapter.resolve_jd(_job(description=""), handler)

    assert source == "form_description"
    assert jd == "Join Acme as a Backend Engineer"
    web.assert_not_called()


def test_jd_source_is_web_search_as_the_last_resort():
    import dataclasses

    adapter = GoogleFormsAdapter()
    handler = _handler(_page_with_heading(""))

    def fake_search(lead):
        return dataclasses.replace(lead, jd_excerpt="Scraped JD text about widgets.")

    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search",
               side_effect=fake_search):
        jd, source = adapter.resolve_jd(_job(description=""), handler)

    assert source == "web_search"
    assert jd == "Scraped JD text about widgets."


def test_resolve_jd_survives_a_failing_form_read():
    adapter = GoogleFormsAdapter()
    page = MagicMock()
    page.locator.side_effect = RuntimeError("detached frame")
    handler = _handler(page)

    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search",
               side_effect=lambda lead: lead):
        jd, source = adapter.resolve_jd(_job(), handler)

    assert (jd, source) == ("", "none")


# ---------------------------------------------------------------------------
# ...and the JD actually lands in QuestionEngine.company_context
# ---------------------------------------------------------------------------

@pytest.fixture
def launched_browser():
    with patch("src.applications.adapters.google_forms_adapter.LaunchedBrowser") as lb_cls:
        page = _page_with_heading("Join Acme as a Backend Engineer")
        lb_cls.return_value.__enter__.return_value = MagicMock(page=page)
        yield page


def _run_apply(job, tmp_path, launched_browser):
    """Runs the real adapter with the real handler; only execute() is faked,
    so the handler (and its QuestionEngine) is genuinely constructed."""
    captured = {}

    def fake_execute(self):
        captured["company_context"] = self.engine.company_context
        return {"status": "COMPLETED", "telemetry": {}}

    with patch.object(GoogleFormsHandler, "execute", fake_execute):
        result = GoogleFormsAdapter().apply(
            {**job, "execution_dir": str(tmp_path)},
            resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True,
        )
    return captured, result


def test_db_matched_jd_reaches_question_engine_company_context(tmp_path, launched_browser):
    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search") as web:
        captured, result = _run_apply(_job(description="We build widgets in Python."), tmp_path, launched_browser)

    assert captured["company_context"] == "We build widgets in Python."
    assert result.jd_source == "db_match"
    web.assert_not_called()


def test_form_description_reaches_question_engine_company_context(tmp_path, launched_browser):
    with patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search") as web:
        captured, result = _run_apply(_job(description=""), tmp_path, launched_browser)

    assert captured["company_context"] == "Join Acme as a Backend Engineer"
    assert result.jd_source == "form_description"
    web.assert_not_called()


# ---------------------------------------------------------------------------
# Exception guard + execution_dir
# ---------------------------------------------------------------------------

def test_a_dead_forms_link_returns_a_diagnosed_failure_not_an_unhandled_exception(tmp_path, launched_browser):
    launched_browser.goto.side_effect = RuntimeError("net::ERR_NAME_NOT_RESOLVED")

    result = GoogleFormsAdapter().apply(
        {**_job(), "execution_dir": str(tmp_path)},
        resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True,
    )

    assert result.status == "FAILED"
    assert "ERR_NAME_NOT_RESOLVED" in result.failure_reason
    assert result.screenshot_path.endswith("error_state.png")
    launched_browser.screenshot.assert_called_once()


def test_execution_dir_fallback_is_absolute_and_under_backend_executions(launched_browser):
    """The fallback was a relative "executions/job_<id>", which scattered
    audit directories wherever the process happened to be launched from."""
    import os
    import shutil

    from src.applications.adapters.google_forms_adapter import _EXECUTIONS_DIR

    assert os.path.isabs(_EXECUTIONS_DIR)
    assert os.path.basename(os.path.dirname(_EXECUTIONS_DIR)) == "backend"

    expected = os.path.join(_EXECUTIONS_DIR, "job_job-1")
    try:
        with patch.object(GoogleFormsHandler, "execute", lambda self: {"status": "COMPLETED", "telemetry": {}}), \
             patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search",
                   side_effect=lambda lead: lead):
            GoogleFormsAdapter().apply(
                _job(execution_dir=""), resume_path="/tmp/resume.pdf",
                profile_manager=MagicMock(), test_mode=True,
            )
        assert os.path.isdir(expected)
    finally:
        shutil.rmtree(expected, ignore_errors=True)
