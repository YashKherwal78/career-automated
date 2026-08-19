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


@patch("src.ingestion.routing.is_endpoint_verified", return_value=False)
@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_refuses_to_route_unverified_known_ats(mock_get, mock_is_verified):
    """A recognized-but-unverified endpoint used to be auto-"verified" by
    inserting a guessed row into the live 62k-row ats_registry table (with a
    NULL company_id, a vendor host instead of a tenant domain, and -- on
    Postgres -- a provider_id that may violate the ats_providers FK). It now
    stays unroutable so the lead lands in human review instead."""
    mock_get.return_value = MagicMock(status_code=200, text="grnhse.com", url="https://boards.greenhouse.io/acme")
    connector, reason = resolve_connector("https://boards.greenhouse.io/acme/jobs/1")
    assert connector is None
    assert "not verified" in reason


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_rejects_non_200_apply_link(mock_get):
    """A dead posting's URL still matches the vendor pattern -- only the
    response status tells them apart."""
    mock_get.return_value = MagicMock(status_code=404, text="grnhse.com", url="https://boards.greenhouse.io/acme")
    connector, reason = resolve_connector("https://boards.greenhouse.io/acme/jobs/1")
    assert connector is None
    assert "404" in reason


def test_routing_does_not_import_any_ats_registry_writer():
    import src.ingestion.routing as routing
    assert not hasattr(routing, "mark_endpoint_verified")


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_none_for_unrecognized_url(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="nothing recognizable here", url="https://example.com/apply")
    connector, reason = resolve_connector("https://example.com/apply")
    assert connector is None
    assert reason == "unrecognized URL"


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_routes_a_bare_email_address_without_fetching(mock_get):
    connector, reason = resolve_connector("jobs@acme.com")
    assert connector == "email_apply"
    assert reason == "email_apply"
    mock_get.assert_not_called()


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_routes_a_mailto_link_without_fetching(mock_get):
    connector, reason = resolve_connector("mailto:jobs@acme.com")
    assert connector == "email_apply"
    assert reason == "email_apply"
    mock_get.assert_not_called()


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_does_not_misroute_a_url_as_email(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="nothing recognizable here", url="https://example.com/apply")
    connector, reason = resolve_connector("https://example.com/apply?ref=jobs@acme.com")
    assert connector != "email_apply"
