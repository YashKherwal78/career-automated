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
