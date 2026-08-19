from unittest.mock import MagicMock, patch
from src.ingestion.email_extractor import scan_job_alerts


@patch("src.ingestion.email_extractor.get_connection")
@patch("src.ingestion.email_extractor.EmailListener")
def test_scan_job_alerts_skips_already_processed(mock_listener_cls, mock_get_connection):
    mock_listener = MagicMock()
    mock_listener.search_job_alerts.return_value = [
        {"message_id": "seen-1", "sender": "jobs@linkedin.com", "subject": "New jobs for you",
         "body": "Backend Engineer at Acme https://forms.gle/abc123"},
        {"message_id": "new-1", "sender": "jobs@linkedin.com", "subject": "New jobs for you",
         "body": "Frontend Engineer at Beta Inc https://forms.gle/def456"},
    ]
    mock_listener_cls.return_value = mock_listener

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"message_id": "seen-1"},  # already processed
        None,                       # not processed
    ]
    mock_conn.execute.return_value = mock_cursor
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    leads = scan_job_alerts(sender_allowlist=["jobs@linkedin.com"], since_days=3)

    assert len(leads) == 1
    assert leads[0].company == "Beta Inc"
    assert leads[0].apply_link == "https://forms.gle/def456"
    assert leads[0].source == "email"
    assert leads[0].source_ref == "new-1"


from src.ingestion.email_extractor import _parse_email_body


def _conn_returning_unprocessed():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn.execute.return_value = cursor
    return conn


# ---------------------------------------------------------------------------
# A digest email lists several jobs -- every one of them is a lead
# ---------------------------------------------------------------------------

def test_parse_email_body_returns_every_lead_in_a_digest():
    body = (
        "Jobs picked for you\n"
        "Backend Engineer at Acme https://forms.gle/abc123\n"
        "Frontend Engineer at Beta Inc https://forms.gle/def456\n"
        "Data Scientist at Gamma https://forms.gle/ghi789\n"
    )

    parsed = _parse_email_body(body)

    assert [p["apply_link"] for p in parsed] == [
        "https://forms.gle/abc123", "https://forms.gle/def456", "https://forms.gle/ghi789",
    ]
    assert [p["company"] for p in parsed] == ["Acme", "Beta Inc", "Gamma"]


def test_parse_email_body_attributes_each_link_to_the_listing_above_it():
    """The role/company nearest a link is the one that link belongs to; the
    first match in the body belongs to a different job entirely."""
    body = "Backend Engineer at Acme https://a.example/1 Frontend Engineer at Beta https://b.example/2"

    parsed = _parse_email_body(body)

    assert parsed[1]["company"] == "Beta"
    assert parsed[1]["role"] == "Frontend Engineer"


def test_parse_email_body_deduplicates_repeated_links():
    body = "Backend Engineer at Acme https://forms.gle/abc123 ... apply: https://forms.gle/abc123"

    assert len(_parse_email_body(body)) == 1


def test_parse_email_body_returns_empty_list_when_there_is_no_url():
    assert _parse_email_body("We received your application. Thanks!") == []


@patch("src.ingestion.email_extractor.get_connection")
@patch("src.ingestion.email_extractor.EmailListener")
def test_scan_job_alerts_yields_every_job_in_one_digest_email(mock_listener_cls, mock_get_connection):
    mock_listener_cls.return_value.search_job_alerts.return_value = [{
        "message_id": "digest-1", "sender": "jobs@linkedin.com", "subject": "3 new jobs",
        "body": ("Backend Engineer at Acme https://forms.gle/abc123\n"
                 "Frontend Engineer at Beta Inc https://forms.gle/def456\n"),
    }]
    mock_get_connection.return_value.__enter__.return_value = _conn_returning_unprocessed()

    leads = scan_job_alerts(sender_allowlist=["jobs@linkedin.com"])

    assert [l.company for l in leads] == ["Acme", "Beta Inc"]
    assert all(l.source_ref == "digest-1" for l in leads)


# ---------------------------------------------------------------------------
# Don't burn a message we failed to parse
# ---------------------------------------------------------------------------

@patch("src.ingestion.email_extractor.get_connection")
@patch("src.ingestion.email_extractor.EmailListener")
def test_an_unparseable_email_is_not_marked_processed(mock_listener_cls, mock_get_connection):
    """Marking on failure burns the message permanently -- a later parser
    improvement could extract it, but the scan would never look again."""
    mock_listener_cls.return_value.search_job_alerts.return_value = [{
        "message_id": "junk-1", "sender": "jobs@linkedin.com", "subject": "Newsletter",
        "body": "No links here at all.",
    }]
    conn = _conn_returning_unprocessed()
    mock_get_connection.return_value.__enter__.return_value = conn

    assert scan_job_alerts(sender_allowlist=["jobs@linkedin.com"]) == []
    assert not any("INSERT INTO processed_job_alert_emails" in str(c.args[0])
                   for c in conn.execute.call_args_list)


@patch("src.ingestion.email_extractor.get_connection")
@patch("src.ingestion.email_extractor.EmailListener")
def test_an_email_with_links_but_no_complete_lead_is_not_marked_processed(mock_listener_cls, mock_get_connection):
    mock_listener_cls.return_value.search_job_alerts.return_value = [{
        "message_id": "partial-1", "sender": "jobs@linkedin.com", "subject": "Update",
        "body": "Click here https://forms.gle/abc123",
    }]
    conn = _conn_returning_unprocessed()
    mock_get_connection.return_value.__enter__.return_value = conn

    assert scan_job_alerts(sender_allowlist=["jobs@linkedin.com"]) == []
    assert not any("INSERT INTO processed_job_alert_emails" in str(c.args[0])
                   for c in conn.execute.call_args_list)


@patch("src.ingestion.email_extractor.get_connection")
@patch("src.ingestion.email_extractor.EmailListener")
def test_a_successfully_extracted_email_is_marked_processed(mock_listener_cls, mock_get_connection):
    mock_listener_cls.return_value.search_job_alerts.return_value = [{
        "message_id": "good-1", "sender": "jobs@linkedin.com", "subject": "1 new job",
        "body": "Backend Engineer at Acme https://forms.gle/abc123",
    }]
    conn = _conn_returning_unprocessed()
    mock_get_connection.return_value.__enter__.return_value = conn

    assert len(scan_job_alerts(sender_allowlist=["jobs@linkedin.com"])) == 1
    assert any("INSERT INTO processed_job_alert_emails" in str(c.args[0])
               for c in conn.execute.call_args_list)


# ---------------------------------------------------------------------------
# CLI entry point (scan_job_alerts had no caller outside tests)
# ---------------------------------------------------------------------------

def test_gmail_scan_script_feeds_every_lead_through_the_pipeline(monkeypatch, tmp_path):
    import importlib.util
    import os
    import sys

    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "run_gmail_job_alert_scan.py")
    spec = importlib.util.spec_from_file_location("run_gmail_job_alert_scan", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from src.ingestion.job_lead import JobLead
    fake_leads = [
        JobLead(company="Acme", role="Backend Engineer", apply_link="https://forms.gle/a",
                location=None, jd_excerpt=None, source="email", source_ref="m-1"),
        JobLead(company="Beta", role="Frontend Engineer", apply_link="https://forms.gle/b",
                location=None, jd_excerpt=None, source="email", source_ref="m-1"),
    ]
    monkeypatch.setattr(module, "scan_job_alerts", lambda sender_allowlist, since_days: fake_leads)

    calls = []
    monkeypatch.setattr(module, "run_lead", lambda lead, user_id, test_mode: (
        calls.append((lead.company, user_id, test_mode)) or {"status": "COMPLETED", "run_id": "r"}
    ))
    monkeypatch.setattr(sys, "argv", ["run_gmail_job_alert_scan.py", "--user-id", "user-1"])

    module.main()

    assert calls == [("Acme", "user-1", True), ("Beta", "user-1", True)], "dry-run by default"
