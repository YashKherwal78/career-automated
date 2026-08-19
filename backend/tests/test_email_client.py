from unittest.mock import MagicMock, patch
import pytest

from src.outreach.email_client import EmailClient, ResumeAttachmentError


def _client():
    with patch("src.outreach.email_client.Config") as mock_config:
        mock_config.GMAIL_ADDRESS = "me@example.com"
        mock_config.GMAIL_APP_PASSWORD = "app-password"
        return EmailClient()


def test_dry_run_with_extra_attachment_does_not_touch_smtp(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4 fake resume")
    cover_letter = tmp_path / "cover_letter.pdf"
    cover_letter.write_bytes(b"%PDF-1.4 fake cover letter")

    client = _client()
    with patch("src.outreach.email_client.smtplib.SMTP") as mock_smtp:
        result = client.send_email(
            to_email="jobs@acme.com", subject="Application", body="See attached.",
            resume_path=str(resume), extra_attachment_path=str(cover_letter), dry_run=True,
        )

    assert result is True
    mock_smtp.assert_not_called()


def test_real_send_attaches_both_resume_and_extra_attachment(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4 fake resume")
    cover_letter = tmp_path / "cover_letter.pdf"
    cover_letter.write_bytes(b"%PDF-1.4 fake cover letter")

    client = _client()
    with patch("src.outreach.email_client.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = client.send_email(
            to_email="jobs@acme.com", subject="Application", body="See attached.",
            resume_path=str(resume), extra_attachment_path=str(cover_letter), dry_run=False,
        )

    assert result is True
    mock_server.send_message.assert_called_once()
    sent_msg = mock_server.send_message.call_args.args[0]
    # 1 text part + 2 attachment parts.
    assert len(sent_msg.get_payload()) == 3
    attachment_filenames = {
        part.get_filename() for part in sent_msg.get_payload() if part.get_filename()
    }
    assert attachment_filenames == {"resume.pdf", "cover_letter.pdf"}


def test_extra_attachment_is_optional_existing_single_attachment_behavior_unchanged(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4 fake resume")

    client = _client()
    with patch("src.outreach.email_client.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = client.send_email(
            to_email="jobs@acme.com", subject="Application", body="See attached.",
            resume_path=str(resume), dry_run=False,
        )

    assert result is True
    sent_msg = mock_server.send_message.call_args.args[0]
    assert len(sent_msg.get_payload()) == 2


def test_missing_extra_attachment_path_raises():
    # Calls the undecorated function directly -- send_email is wrapped in
    # a @retry that retries any non-auth exception with real exponential
    # backoff (pre-existing behavior, not introduced here), which would
    # otherwise make this assertion cost several real seconds of sleep to
    # confirm a pure validation error.
    client = _client()
    with pytest.raises(ResumeAttachmentError):
        EmailClient.send_email.__wrapped__(
            client, to_email="jobs@acme.com", subject="x", body="x",
            extra_attachment_path="/nonexistent/cover_letter.pdf", dry_run=True,
        )
