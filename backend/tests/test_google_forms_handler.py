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
    # Audited separately below; stubbed here so the spy only records the fill
    # pass (the per-section audit re-extracts the same section by design).
    handler._pre_submit_audit = lambda: True

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
    handler._pre_submit_audit = lambda: True

    safe_to_submit = handler._process_custom_fields({})

    assert safe_to_submit is False
    assert state["section"] == 0


# ---------------------------------------------------------------------------
# Per-section pre-submit audit
# ---------------------------------------------------------------------------

def test_earlier_section_audit_failure_blocks_submission_even_if_last_section_is_clean():
    """base_handler.execute() runs _pre_submit_audit() once, AFTER the whole
    multi-section walk -- at which point only the final section exists in the
    DOM, so sections 1..n-1 were never audited by this codebase at all. Here
    section 1 fails its audit and section 2 passes; the walk must still come
    back unsafe."""
    page, state = _make_multi_section_page(section_count=2)
    handler = _make_handler(page)
    handler.active_context = page
    handler._extract_questions = lambda: []

    audited = []

    def audit():
        audited.append(state["section"])
        return state["section"] != 0  # section 1 (index 0) has an empty required field

    handler._pre_submit_audit = audit

    telemetry = {}
    safe_to_submit = handler._process_custom_fields(telemetry)

    assert audited == [0, 1], "every section must be audited while it is still on screen"
    assert safe_to_submit is False
    assert telemetry["form_sections_processed"] == 2, "the walk still completes, so telemetry is complete"
    assert any(m["type"] == "SECTION_AUDIT_FAILED" for m in telemetry["missing_fields"])


# ---------------------------------------------------------------------------
# ARIA widget interaction (Google Forms renders no native form elements)
# ---------------------------------------------------------------------------

class _FakeEl:
    """A Google Forms option div: identified by aria-label, state carried in
    aria-checked/aria-selected, no native input anywhere."""

    def __init__(self, label, checked=False, selected=False, text=None):
        self.attrs = {
            "aria-label": label,
            "aria-checked": "true" if checked else "false",
            "aria-selected": "true" if selected else "false",
        }
        self._text = label if text is None else text
        self.clicks = 0

    def get_attribute(self, name):
        return self.attrs.get(name)

    def text_content(self):
        return self._text

    def click(self, **kwargs):
        self.clicks += 1
        self.attrs["aria-checked"] = "false" if self.attrs["aria-checked"] == "true" else "true"
        self.attrs["aria-selected"] = "true"


class _FakeLocator:
    def __init__(self, els):
        self.els = els

    def all(self):
        return self.els

    def count(self):
        return len(self.els)

    @property
    def first(self):
        return self.els[0] if self.els else _FakeEl("")


class _FakeContainer:
    def __init__(self, by_selector):
        self.by_selector = by_selector

    def locator(self, selector):
        return _FakeLocator(self.by_selector.get(selector, []))


def _radio_container(*labels):
    return _FakeContainer({'div[role="radio"]': [_FakeEl(l) for l in labels]})


def test_radio_group_clicks_the_matching_aria_option():
    handler = _make_handler(MagicMock())
    container = _radio_container("Yes", "No")
    interaction = {}

    ok = handler._interact_widget("radio_group", container, "No", interaction)

    els = container.by_selector['div[role="radio"]']
    assert ok is True
    assert els[1].clicks == 1 and els[1].get_attribute("aria-checked") == "true"
    assert els[0].clicks == 0, "the non-matching option must not be touched"


def test_radio_group_prefers_exact_label_over_substring():
    handler = _make_handler(MagicMock())
    container = _radio_container("Yes, with sponsorship", "Yes")

    assert handler._interact_widget("radio_group", container, "Yes", {}) is True
    els = container.by_selector['div[role="radio"]']
    assert els[1].clicks == 1 and els[0].clicks == 0


def test_radio_group_returns_false_when_no_option_matches():
    handler = _make_handler(MagicMock())
    container = _radio_container("Yes", "No")

    assert handler._interact_widget("radio_group", container, "Maybe", {}) is False


def test_radio_group_leaves_an_already_selected_option_alone():
    handler = _make_handler(MagicMock())
    container = _FakeContainer({'div[role="radio"]': [_FakeEl("Yes", checked=True), _FakeEl("No")]})

    assert handler._interact_widget("radio_group", container, "Yes", {}) is True
    els = container.by_selector['div[role="radio"]']
    assert els[0].clicks == 0, "clicking an already-checked option would toggle it back off"
    assert els[0].get_attribute("aria-checked") == "true"


def test_checkbox_group_checks_every_comma_separated_answer():
    handler = _make_handler(MagicMock())
    container = _FakeContainer({
        'div[role="checkbox"]': [_FakeEl("Python"), _FakeEl("Go"), _FakeEl("Rust")]
    })

    assert handler._interact_widget("checkbox_group", container, "Python, Rust", {}) is True
    els = container.by_selector['div[role="checkbox"]']
    assert [e.get_attribute("aria-checked") for e in els] == ["true", "false", "true"]


def test_checkbox_group_does_not_split_an_option_that_genuinely_contains_a_comma():
    handler = _make_handler(MagicMock())
    container = _FakeContainer({
        'div[role="checkbox"]': [_FakeEl("Yes, I am authorized"), _FakeEl("No")]
    })

    assert handler._interact_widget("checkbox_group", container, "Yes, I am authorized", {}) is True
    els = container.by_selector['div[role="checkbox"]']
    assert els[0].get_attribute("aria-checked") == "true"


def test_native_select_opens_the_aria_listbox_then_clicks_the_option():
    handler = _make_handler(MagicMock())
    listbox = _FakeEl("Choose")
    options = [_FakeEl("Remote"), _FakeEl("On-site")]
    container = _FakeContainer({'div[role="listbox"]': [listbox], 'div[role="option"]': options})
    interaction = {}

    ok = handler._interact_widget("native_select", container, "On-site", interaction)

    assert ok is True
    assert listbox.clicks == 1, "Google's dropdown options aren't clickable until the listbox is opened"
    assert options[1].clicks == 1 and options[0].clicks == 0
    assert "listbox" in interaction["Selector Used"]


def test_native_select_returns_false_when_no_option_matches():
    handler = _make_handler(MagicMock())
    page = MagicMock()
    handler.active_context = page
    page.locator.return_value.all.return_value = []
    container = _FakeContainer({
        'div[role="listbox"]': [_FakeEl("Choose")],
        'div[role="option"]': [_FakeEl("Remote")],
    })

    assert handler._interact_widget("native_select", container, "Hybrid", {}) is False


def test_input_widget_still_uses_the_base_class_native_html_path():
    """Only the three ARIA-backed types are diverted; a Google Form's short-
    answer question is a real <input> and must keep the shared code path."""
    handler = _make_handler(MagicMock())
    handler._interact_custom_dropdown = MagicMock(return_value=True)
    container = MagicMock()

    handler._interact_widget("input", container, "Yash", {})

    handler._interact_custom_dropdown.assert_not_called()


def test_radio_question_is_filled_and_reported_filled_end_to_end():
    """The multi-page tests stub _extract_questions to []. This one pushes a
    real question dict through _process_custom_fields -> _interact_widget ->
    _interact_custom_dropdown, so a regression in the ARIA interaction shows
    up as an unfilled widget rather than only as a page-walk that still runs."""
    page = MagicMock()
    handler = _make_handler(page)
    handler.active_context = page
    container = _radio_container("Yes", "No")
    handler._extract_questions = lambda: [{
        "container": container,
        "question": "Are you authorized to work in the US?",
        "raw_label": "Are you authorized to work in the US? *",
        "is_required": True,
        "widget_type": "radio_group",
        "options": ["Yes", "No"],
        "placeholder": "",
    }]
    handler._advance_to_next_page = lambda: False
    handler._pre_submit_audit = lambda: True
    handler.engine.answer = MagicMock(return_value="Yes")

    telemetry = {"question_count": 0, "llm_question_count": 0, "profile_question_count": 0}
    safe_to_submit = handler._process_custom_fields(telemetry)

    assert safe_to_submit is True
    assert telemetry["interaction_log"][-1]["Verification Result"] is True
    assert container.by_selector['div[role="radio"]'][0].get_attribute("aria-checked") == "true"


# ---------------------------------------------------------------------------
# Pre-submit audit of ARIA widgets
# ---------------------------------------------------------------------------

def test_audit_reports_a_checked_aria_radio_group_as_filled():
    """base_handler's audit looks for a checked <input>, of which a Google
    Form has none -- so without this override every correctly-answered
    multiple-choice question audited as an empty required field."""
    handler = _make_handler(MagicMock())
    container = _FakeContainer({'div[role="radio"]': [_FakeEl("Yes", checked=True), _FakeEl("No")]})

    assert handler._custom_field_is_empty(container, "radio_group") is False


def test_audit_reports_an_unchecked_aria_radio_group_as_empty():
    handler = _make_handler(MagicMock())
    container = _radio_container("Yes", "No")

    assert handler._custom_field_is_empty(container, "radio_group") is True


def test_audit_reads_aria_selected_for_a_listbox():
    handler = _make_handler(MagicMock())
    filled = _FakeContainer({'div[role="option"]': [_FakeEl("Remote", selected=True)]})
    empty = _FakeContainer({'div[role="option"]': [_FakeEl("Remote")]})

    assert handler._custom_field_is_empty(filled, "native_select") is False
    assert handler._custom_field_is_empty(empty, "native_select") is True


def test_audit_defers_to_the_generic_check_for_non_aria_widgets():
    handler = _make_handler(MagicMock())

    assert handler._custom_field_is_empty(MagicMock(), "input") is None
