from unittest.mock import MagicMock, patch

from src.applications.adapters.email_apply_adapter import EmailApplyAdapter


def _job(**overrides):
    base = dict(
        job_title="Backend Engineer", company_name="Acme",
        apply_url="jobs@acme.com", description="We need a backend engineer.",
    )
    base.update(overrides)
    return base


def _profile_manager():
    pm = MagicMock()
    pm.get_field.side_effect = lambda k: {"email": "candidate@example.com", "first_name": "Jane", "last_name": "Doe"}.get(k, "")
    return pm


@patch("src.applications.adapters.email_apply_adapter.EmailClient")
@patch("src.applications.adapters.email_apply_adapter.generate_cover_letter_pdf", return_value=None)
@patch("src.applications.adapters.email_apply_adapter.draft_email_apply_pitch", return_value=("Application: Backend Engineer at Acme", "I'm applying for this role. Resume and cover letter attached."))
def test_apply_returns_review_required_when_no_email_address(mock_draft, mock_cover_letter, mock_email_client_cls):
    adapter = EmailApplyAdapter()
    result = adapter.apply(_job(apply_url=""), resume_path="/tmp/resume.pdf", profile_manager=_profile_manager(), test_mode=True, user_id="user-1")

    assert result.status == "REVIEW_REQUIRED"
    mock_email_client_cls.assert_not_called()


@patch("src.applications.adapters.email_apply_adapter.EmailClient")
@patch("src.applications.adapters.email_apply_adapter.generate_cover_letter_pdf", return_value=None)
@patch("src.applications.adapters.email_apply_adapter.draft_email_apply_pitch", return_value=("Application: Backend Engineer at Acme", "I'm applying for this role. Resume and cover letter attached."))
def test_apply_dry_run_never_marks_really_submitted(mock_draft, mock_cover_letter, mock_email_client_cls):
    mock_email_client_cls.return_value.send_email.return_value = True
    adapter = EmailApplyAdapter()

    result = adapter.apply(_job(), resume_path="/tmp/resume.pdf", profile_manager=_profile_manager(), test_mode=True, user_id="user-1")

    assert result.status == "COMPLETED"
    assert result.really_submitted is False
    call_kwargs = mock_email_client_cls.return_value.send_email.call_args.kwargs
    assert call_kwargs["dry_run"] is True
    assert call_kwargs["to_email"] == "jobs@acme.com"
    assert call_kwargs["resume_path"] == "/tmp/resume.pdf"


@patch("src.applications.adapters.email_apply_adapter.EmailClient")
@patch("src.applications.adapters.email_apply_adapter.generate_cover_letter_pdf")
@patch("src.applications.adapters.email_apply_adapter.draft_email_apply_pitch", return_value=("Application: Backend Engineer at Acme", "I'm applying for this role. Resume and cover letter attached."))
def test_apply_live_send_marks_really_submitted_and_attaches_cover_letter(mock_draft, mock_cover_letter, mock_email_client_cls, tmp_path):
    cover_letter = tmp_path / "cl_dir" / "cover_letter.pdf"
    cover_letter.parent.mkdir()
    cover_letter.write_bytes(b"%PDF-1.4 fake")
    mock_cover_letter.return_value = str(cover_letter)
    mock_email_client_cls.return_value.send_email.return_value = True

    adapter = EmailApplyAdapter()
    result = adapter.apply(_job(), resume_path="/tmp/resume.pdf", profile_manager=_profile_manager(), test_mode=False, user_id="user-1")

    assert result.status == "COMPLETED"
    assert result.really_submitted is True
    call_kwargs = mock_email_client_cls.return_value.send_email.call_args.kwargs
    assert call_kwargs["dry_run"] is False
    assert call_kwargs["extra_attachment_path"] == str(cover_letter)


@patch("src.applications.adapters.email_apply_adapter.EmailClient")
@patch("src.applications.adapters.email_apply_adapter.generate_cover_letter_pdf", return_value=None)
@patch("src.applications.adapters.email_apply_adapter.draft_email_apply_pitch", side_effect=ValueError("LLM returned an incomplete draft"))
def test_apply_returns_failed_when_composition_raises(mock_draft, mock_cover_letter, mock_email_client_cls):
    adapter = EmailApplyAdapter()
    result = adapter.apply(_job(), resume_path="/tmp/resume.pdf", profile_manager=_profile_manager(), test_mode=True, user_id="user-1")

    assert result.status == "FAILED"
    assert "incomplete draft" in result.failure_reason
    mock_email_client_cls.return_value.send_email.assert_not_called()


def test_email_apply_registered_in_dispatcher():
    from src.applications.dispatcher import ApplicationDispatcher
    assert ApplicationDispatcher._ADAPTER_REGISTRY["email_apply"] == (
        "src.applications.adapters.email_apply_adapter", "EmailApplyAdapter",
    )
