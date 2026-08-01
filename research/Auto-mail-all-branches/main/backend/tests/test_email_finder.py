"""Unit tests for email discovery helpers (no external API calls)."""

from __future__ import annotations

from utils.email_finder import extract_email_from_text, find_recruiter_email


def test_extract_email_from_text_empty():
    assert extract_email_from_text("") == (None, "jd_text")


def test_extract_email_from_text_finds_personal_over_generic():
    text = "Apply at careers@corp.com or email jane.smith@corp.com directly."
    email, source = extract_email_from_text(text)
    assert source == "jd_text"
    assert email == "jane.smith@corp.com"


def test_find_recruiter_email_stops_at_jd_text():
    """JD regex path should return before any Hunter / API usage."""
    email, source, contacts = find_recruiter_email(
        jd_text="Questions? jane.smith@example.org",
        additional_context="",
        recruiter_name="",
        recruiter_linkedin_url="",
        company_website="",
        company_domain="",
        hunter_api_key="",
        getprospect_api_key="",
        apollo_api_key="",
        snov_api_key="",
        progress_log=None,
    )
    assert email == "jane.smith@example.org"
    assert source == "jd_text"
    assert len(contacts) == 1
    assert contacts[0]["email"] == "jane.smith@example.org"
