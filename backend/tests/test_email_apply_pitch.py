import json
from unittest.mock import MagicMock

from src.applications.email_apply_pitch import draft_email_apply_pitch


def _fake_llm(subject="Backend Engineer role at Acme", body="I'm applying for the Backend Engineer role at Acme. I built a system handling 10k requests/sec. Resume and cover letter attached."):
    llm = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps({"subject": subject, "body": body})))]
    llm.chat_completion.return_value = response
    return llm


def test_draft_email_apply_pitch_returns_subject_and_body():
    profile_manager = MagicMock()
    profile_manager.get_field.side_effect = lambda k: {"first_name": "Jane", "last_name": "Doe"}.get(k, "")
    profile_manager.get_llm_context.return_value = "10k requests/sec"

    subject, body = draft_email_apply_pitch(
        job_title="Backend Engineer", company_name="Acme",
        jd_text="We need someone who can handle 10k requests/sec.",
        profile_manager=profile_manager, llm_client=_fake_llm(), user_id="user-1",
    )

    assert subject
    assert body
    assert "Jane Doe" in body


def test_draft_email_apply_pitch_raises_on_incomplete_llm_response():
    profile_manager = MagicMock()
    profile_manager.get_field.return_value = ""
    profile_manager.get_llm_context.return_value = ""

    llm = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps({"subject": "", "body": ""})))]
    llm.chat_completion.return_value = response

    try:
        draft_email_apply_pitch(
            job_title="Backend Engineer", company_name="Acme", jd_text="",
            profile_manager=profile_manager, llm_client=llm, user_id="user-1",
        )
        assert False, "expected a ValueError"
    except ValueError:
        pass


def test_draft_email_apply_pitch_strips_banned_phrases():
    profile_manager = MagicMock()
    profile_manager.get_field.return_value = ""
    profile_manager.get_llm_context.return_value = ""

    llm = _fake_llm(body="I'm excited about this great fit opportunity. Attached are my resume and cover letter.")

    _, body = draft_email_apply_pitch(
        job_title="Backend Engineer", company_name="Acme", jd_text="",
        profile_manager=profile_manager, llm_client=llm, user_id="user-1",
    )

    assert "excited about" not in body.lower()
    assert "great fit" not in body.lower()
