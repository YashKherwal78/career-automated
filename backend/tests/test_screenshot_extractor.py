import json
from unittest.mock import MagicMock, patch
from src.ingestion.screenshot_extractor import extract_from_image


def _fake_router(payload: dict):
    router = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    router.chat_completion_vision.return_value = response
    return router


def test_extract_from_image_returns_lead_on_valid_response(tmp_path):
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = _fake_router({
        "company": "Acme", "role": "Backend Engineer",
        "apply_link": "https://forms.gle/abc123", "location": "Remote",
        "jd_excerpt": "Build things.", "confidence": 0.9,
    })

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is not None
    assert lead.company == "Acme"
    assert lead.apply_link == "https://forms.gle/abc123"
    assert lead.source == "screenshot"
    assert lead.source_ref == str(img)


def test_extract_from_image_returns_none_on_low_confidence(tmp_path):
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = _fake_router({
        "company": "Acme", "role": "Backend Engineer",
        "apply_link": "https://forms.gle/abc123", "location": None,
        "jd_excerpt": None, "confidence": 0.2,
    })

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is None


def test_extract_from_image_returns_none_on_unparseable_json(tmp_path):
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="not json"))]
    router.chat_completion_vision.return_value = response

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is None


def test_extract_from_image_puts_an_email_apply_address_in_apply_link(tmp_path):
    """When the post says "email your CV to jobs@acme.com" instead of
    giving a link, the model should put the address in apply_link -- same
    field, routing.py decides what to do with it based on its shape."""
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = _fake_router({
        "company": "Acme", "role": "Backend Engineer",
        "apply_link": "jobs@acme.com", "location": None,
        "jd_excerpt": None, "confidence": 0.9,
    })

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is not None
    assert lead.apply_link == "jobs@acme.com"


def test_prompt_instructs_the_model_to_extract_an_email_apply_address():
    from src.ingestion.screenshot_extractor import _PROMPT
    assert "email" in _PROMPT.lower()


def test_extract_from_image_returns_none_for_an_unreadable_file():
    """The open() was outside the try, so a missing/unreadable file raised
    instead of returning None -- contradicting this function's own contract
    and killing a whole batch run over one bad image."""
    from src.ingestion.screenshot_extractor import extract_from_image

    assert extract_from_image("/nonexistent/definitely-not-here.png", llm_router=MagicMock()) is None
