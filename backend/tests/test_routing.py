from unittest.mock import MagicMock, patch
from src.discovery.ats_detector import GoogleFormsSignature


def test_google_forms_signature_detects_forms_gle():
    detector = GoogleFormsSignature()
    response = MagicMock(status_code=200, text="")
    assert detector.detect("https://forms.gle/AbCdEf123", response) is True


def test_google_forms_signature_detects_docs_google_forms():
    detector = GoogleFormsSignature()
    response = MagicMock(status_code=200, text="")
    assert detector.detect("https://docs.google.com/forms/d/e/1FAIpQ/viewform", response) is True


def test_google_forms_signature_rejects_unrelated_url():
    detector = GoogleFormsSignature()
    response = MagicMock(status_code=200, text="")
    assert detector.detect("https://boards.greenhouse.io/acme/jobs/123", response) is False


def test_google_forms_signature_provider_id():
    assert GoogleFormsSignature().provider_id == "google_forms"


from src.ingestion.routing import resolve_connector


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_google_forms_directly(mock_get):
    connector, reason = resolve_connector("https://forms.gle/AbCdEf123")
    assert connector == "google_forms"
    assert reason == "google_forms"
    mock_get.assert_not_called()  # no fetch needed for Google Forms — URL pattern is enough


@patch("src.ingestion.routing.is_endpoint_verified", return_value=True)
@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_verified_known_ats(mock_get, mock_is_verified):
    mock_get.return_value = MagicMock(status_code=200, text="grnhse.com", url="https://boards.greenhouse.io/acme")
    connector, reason = resolve_connector("https://boards.greenhouse.io/acme/jobs/1")
    assert connector == "greenhouse"
    assert "verified" in reason


@patch("src.ingestion.routing.mark_endpoint_verified")
@patch("src.ingestion.routing.is_endpoint_verified", return_value=False)
@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_verifies_unverified_known_ats(mock_get, mock_is_verified, mock_mark):
    mock_get.return_value = MagicMock(status_code=200, text="grnhse.com", url="https://boards.greenhouse.io/acme")
    connector, reason = resolve_connector("https://boards.greenhouse.io/acme/jobs/1")
    assert connector == "greenhouse"
    assert "newly verified" in reason
    mock_mark.assert_called_once()


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_none_for_unrecognized_url(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="nothing recognizable here", url="https://example.com/apply")
    connector, reason = resolve_connector("https://example.com/apply")
    assert connector is None
    assert reason == "unrecognized URL"
