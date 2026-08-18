from unittest.mock import MagicMock
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
