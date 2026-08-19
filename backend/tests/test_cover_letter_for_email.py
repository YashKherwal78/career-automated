from unittest.mock import MagicMock, patch

from src.applications.cover_letter_for_email import generate_cover_letter_pdf


@patch("src.billing.access.has_paid_access", return_value=False)
def test_returns_none_when_user_is_not_paid(mock_paid):
    result = generate_cover_letter_pdf(
        user_id="user-1", candidate_email="user@example.com",
        job_title="Backend Engineer", company_name="Acme", jd_text="Build things.",
    )
    assert result is None


@patch("src.resume_intelligence.cover_letter.pdf_renderer.compile_pdf")
@patch("src.resume_intelligence.cover_letter.generator.CoverLetterGenerator")
@patch("src.api.routers.tailor._load_personal_info", return_value={"full_name": "Jane Doe", "phone": ""})
@patch("src.api.routers.tailor._load_candidate_memory", return_value={"global": ["Built a system handling 10k req/s"]})
@patch("src.api.db.get_connection")
@patch("src.billing.access.has_paid_access", return_value=True)
def test_returns_pdf_path_on_success(mock_paid, mock_conn, mock_memory, mock_personal, mock_generator_cls, mock_compile_pdf, tmp_path):
    mock_conn.return_value.__enter__.return_value = MagicMock()
    fake_result = MagicMock(is_fallback=False, cover_letter_tex="\\documentclass{letter}...")
    mock_generator_cls.return_value.generate.return_value = fake_result

    fake_pdf = tmp_path / "cover_letter.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")
    mock_compile_pdf.return_value = str(fake_pdf)

    result = generate_cover_letter_pdf(
        user_id="user-1", candidate_email="user@example.com",
        job_title="Backend Engineer", company_name="Acme", jd_text="",
    )

    assert result == str(fake_pdf)


@patch("src.resume_intelligence.cover_letter.generator.CoverLetterGenerator")
@patch("src.api.routers.tailor._load_personal_info", return_value={})
@patch("src.api.routers.tailor._load_candidate_memory", return_value={"global": []})
@patch("src.api.db.get_connection")
@patch("src.billing.access.has_paid_access", return_value=True)
def test_returns_none_on_fallback_result(mock_paid, mock_conn, mock_memory, mock_personal, mock_generator_cls):
    mock_conn.return_value.__enter__.return_value = MagicMock()
    fake_result = MagicMock(is_fallback=True, cover_letter_tex="")
    mock_generator_cls.return_value.generate.return_value = fake_result

    result = generate_cover_letter_pdf(
        user_id="user-1", candidate_email="user@example.com",
        job_title="Backend Engineer", company_name="Acme", jd_text="",
    )

    assert result is None
