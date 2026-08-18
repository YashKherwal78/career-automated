from unittest.mock import MagicMock
from src.utils.llm_router import LLMRouter


def test_chat_completion_vision_calls_gemini_with_image_and_text_parts(monkeypatch):
    router = LLMRouter()
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.text = '{"company": "Acme"}'
    fake_response.usage_metadata.total_token_count = 42
    fake_client.models.generate_content.return_value = fake_response
    router.gemini_client = fake_client

    result = router.chat_completion_vision(
        image_bytes=b"fake-png-bytes",
        mime_type="image/png",
        prompt="Extract the company name as JSON.",
        response_format={"type": "json_object"},
    )

    assert result.choices[0].message.content == '{"company": "Acme"}'
    assert result.usage.total_tokens == 42
    call_kwargs = fake_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.0-flash"
    assert call_kwargs["config"].response_mime_type == "application/json"


def test_chat_completion_vision_raises_when_gemini_not_configured():
    router = LLMRouter()
    router.gemini_client = None
    try:
        router.chat_completion_vision(b"x", "image/png", "prompt")
        assert False, "expected an exception"
    except Exception as e:
        assert "Gemini" in str(e)
