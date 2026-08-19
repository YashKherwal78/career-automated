from unittest.mock import MagicMock

from src.applications.handlers.google_forms import GoogleFormsHandler


def _make_handler(page):
    return GoogleFormsHandler(
        page=page, job_title="Backend Engineer", company_name="Acme", location="Remote",
        resume_path="/tmp/resume.pdf", test_mode=True, execution_dir="/tmp/exec",
        profile_manager=MagicMock(), rag_client=MagicMock(), llm_client=MagicMock(),
    )


def _make_multi_section_page(section_count: int, advance_works: bool = True):
    """Builds a MagicMock Playwright Page standing in for a multi-section
    Google Form. Google Forms only renders ONE section's `div[role="listitem"]`
    questions at a time; the rest don't exist in the DOM until "Next" is
    clicked. This fake reproduces exactly that: `state["section"]` is the
    section currently on screen, clicking Next advances it (or, when
    advance_works=False, reproduces Google Forms refusing to advance because
    a required question on this section is still empty), and the "Next"
    button disappears on the final section.
    """
    state = {"section": 0}
    page = MagicMock()

    def locator_side_effect(selector):
        loc = MagicMock()
        if selector == 'div[role="listitem"]':
            # Both signals _current_section_fingerprint() reads. Deliberately
            # different per section so a real advance is distinguishable from
            # a blocked one.
            loc.count.return_value = state["section"] + 1
            heading = MagicMock()
            heading.text_content.return_value = f"Section {state['section']} first question"
            loc.first.locator.return_value.first = heading
        return loc

    def get_by_role_side_effect(role, name=None, **kwargs):
        btn = MagicMock()
        if role == "button" and name == "Next":
            is_last_section = state["section"] >= section_count - 1
            btn.count.return_value = 0 if is_last_section else 1

            def click(*args, **kwargs):
                if advance_works:
                    state["section"] += 1

            btn.first.click.side_effect = click
        return btn

    page.locator.side_effect = locator_side_effect
    page.get_by_role.side_effect = get_by_role_side_effect
    return page, state


def test_read_form_description_returns_text_when_present():
    page = MagicMock()
    page.locator.return_value.first.text_content.return_value = "We are hiring a Backend Engineer to build widgets."
    handler = _make_handler(page)

    description = handler.read_form_description()

    assert description == "We are hiring a Backend Engineer to build widgets."


def test_get_submit_button_locator_finds_submit_span():
    page = MagicMock()
    handler = _make_handler(page)

    handler._get_submit_button_locator()

    page.get_by_role.assert_called_with("button", name="Submit")


def test_extract_questions_tags_file_upload_items_instead_of_input():
    page = MagicMock()
    item = MagicMock()
    item.locator.return_value.first.text_content.return_value = "Attach your resume"
    item.get_by_role.side_effect = lambda role, **kwargs: (
        MagicMock(count=MagicMock(return_value=1)) if role == "button" else MagicMock(all=MagicMock(return_value=[]))
    )
    page.locator.return_value.all.return_value = [item]

    handler = _make_handler(page)
    handler.active_context = page

    questions = handler._extract_questions()

    assert questions[0]["widget_type"] == "file_upload"


def test_file_upload_question_blocks_submission_end_to_end():
    """The tagging test above only proves _extract_questions() labels the item
    "file_upload". This one walks the whole path that label is supposed to
    trigger — QuestionClassifier.classify -> engine.answer -> _interact_widget
    -> _interact_custom_dropdown's default False -> safe_to_submit False — with
    a confident answer mocked in, so the question is NOT skipped as
    unanswerable. It's what would catch a regression if QuestionClassifier
    started escalating/short-circuiting this label, or if _interact_widget grew
    a case that silently accepted "file_upload".
    """
    page = MagicMock()
    handler = _make_handler(page)
    handler.active_context = page
    # Optional, not required — a file upload blocks submission either way
    # (see the comment at the tagging site in google_forms.py).
    handler._extract_questions = lambda: [{
        "container": MagicMock(),
        "question": "Attach your resume",
        "raw_label": "Attach your resume",
        "is_required": False,
        "widget_type": "file_upload",
        "options": [],
        "placeholder": "",
    }]
    handler._advance_to_next_page = lambda: False
    handler.engine.answer = MagicMock(return_value="/tmp/resume.pdf")

    telemetry = {"question_count": 0, "llm_question_count": 0, "profile_question_count": 0}
    safe_to_submit = handler._process_custom_fields(telemetry)

    assert handler.engine.answer.called, "file_upload must reach the engine, not be short-circuited"
    assert safe_to_submit is False
    assert telemetry["interaction_log"][-1]["Verification Result"] is False


def test_process_custom_fields_walks_every_section_extracting_each_exactly_once():
    """The whole point of the multi-page override: base_handler's execute()
    calls _process_custom_fields() once per retry cycle, so without this
    override a 2-section Google Form would only ever have section 1 filled
    (and would then be submitted with section 2 blank, or hang on Next)."""
    page, state = _make_multi_section_page(section_count=2)
    handler = _make_handler(page)
    handler.active_context = page

    extracted_sections = []

    def spy_extract():
        extracted_sections.append(state["section"])
        return []

    handler._extract_questions = spy_extract

    telemetry = {}
    safe_to_submit = handler._process_custom_fields(telemetry)

    assert extracted_sections == [0, 1]
    assert safe_to_submit is True
    assert telemetry["form_sections_processed"] == 2


def test_process_custom_fields_is_unsafe_when_google_forms_refuses_to_advance():
    """Google Forms itself blocks "Next" when a required question on the
    current section is empty. That's a real "this form is not fully filled"
    signal — it must surface as not-safe-to-submit (REVIEW_REQUIRED), not as
    a silent infinite loop or a premature submit."""
    page, state = _make_multi_section_page(section_count=2, advance_works=False)
    handler = _make_handler(page)
    handler.active_context = page
    handler._extract_questions = lambda: []

    safe_to_submit = handler._process_custom_fields({})

    assert safe_to_submit is False
    assert state["section"] == 0
