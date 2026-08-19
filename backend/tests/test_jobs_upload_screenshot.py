import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.routers.jobs import upload_job_screenshot
from src.ingestion.job_lead import JobLead


def _upload_file(filename: str, content: bytes = b"fake-image-bytes"):
    uf = MagicMock()
    uf.filename = filename
    uf.file = io.BytesIO(content)
    return uf


def _user():
    return MagicMock(user_id="user-1")


def test_rejects_unsupported_extension():
    with pytest.raises(HTTPException) as exc_info:
        upload_job_screenshot(file=_upload_file("post.gif"), current_user=_user())
    assert exc_info.value.status_code == 400


@patch("src.ingestion.jd_enrichment.record_lead")
@patch("src.ingestion.screenshot_extractor.extract_from_image")
def test_returns_extracted_fields_on_success(mock_extract, mock_record):
    mock_extract.return_value = JobLead(
        company="Notion", role="Product Engineer", apply_link="https://forms.gle/abc123",
        location="Remote", jd_excerpt="Build the block editor.", source="screenshot", source_ref="/tmp/x.png",
    )

    result = upload_job_screenshot(file=_upload_file("post.png"), current_user=_user())

    assert result["success"] is True
    assert result["company"] == "Notion"
    assert result["role"] == "Product Engineer"
    assert result["apply_link"] == "https://forms.gle/abc123"
    mock_record.assert_called_once()
    call_kwargs = mock_record.call_args.kwargs
    assert call_kwargs["user_id"] == "user-1"
    assert call_kwargs["result_status"] == "EXTRACTED_ONLY"
    assert call_kwargs["really_submitted"] is False


@patch("src.ingestion.jd_enrichment.record_lead")
@patch("src.ingestion.screenshot_extractor.extract_from_image", return_value=None)
def test_returns_failure_message_when_extraction_fails(mock_extract, mock_record):
    result = upload_job_screenshot(file=_upload_file("post.png"), current_user=_user())

    assert result["success"] is False
    assert "message" in result
    mock_record.assert_not_called()


@patch("src.ingestion.screenshot_extractor.extract_from_image")
def test_cleans_up_temp_file_after_processing(mock_extract):
    import os
    written_paths = []

    def _capture_and_return_lead(path):
        written_paths.append(path)
        assert os.path.exists(path)
        return None

    mock_extract.side_effect = _capture_and_return_lead

    upload_job_screenshot(file=_upload_file("post.jpg"), current_user=_user())

    assert len(written_paths) == 1
    assert not os.path.exists(written_paths[0])
