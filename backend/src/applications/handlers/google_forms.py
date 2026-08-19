"""
Google Forms "apply here" links, treated as just another ATS connector.

Two things make this different from every existing handler:

1. There are no ATS-standard fields. A Google Form has no name/email/phone
   input the platform guarantees — everything is an ordinary form item, so
   all of the work happens in the generic _extract_questions() /
   _interact_widget() cycle the base class already owns.
2. A Google Form can be split into SECTIONS, and only the current section
   exists in the DOM at all. Every other handler's form is one page; here,
   filling the form means fill -> Next -> fill -> Next -> ... -> Submit.
   See _process_custom_fields() below for how that loop is grafted onto the
   shared execute() state machine without touching it.
"""
import re

from src.applications.handlers.base_handler import BaseATSHandler
from src.system.logger import setup_logger

logger = setup_logger("google_forms_handler")

# Google Forms' own DOM roles for each question widget type, mapped onto
# the widget_type vocabulary _interact_widget() (base_handler.py) already
# understands.
_WIDGET_TYPE_BY_ROLE = {
    "radio": "radio_group",
    "checkbox": "checkbox_group",
    "listbox": "native_select",
}

# The inverse: which Google ARIA role backs each of those widget_type names.
# These three types keep their base-class names on purpose -- _process_custom_fields
# derives field_type from them ("dropdown"/"multiselect") and QuestionEngine's
# option-normalization keys off that -- but their *interaction* has to be
# Google-specific, because Google Forms renders none of the native HTML the
# base class drives (no <select>, no <input type=radio>, no <label> wrapping
# an input; just divs with role/aria-label/aria-checked).
_ARIA_ROLE_BY_WIDGET_TYPE = {
    "native_select": "listbox",
    "radio_group": "radio",
    "checkbox_group": "checkbox",
}


class GoogleFormsHandler(BaseATSHandler):
    ATS_NAME = "GOOGLE_FORMS"

    # Defensive bound on the fill -> Next -> fill loop. A real application
    # form is a handful of sections; anything past this means the DOM isn't
    # behaving the way this handler assumes, and looping forever inside one
    # execute() cycle is the worst possible failure mode.
    _MAX_FORM_SECTIONS = 25

    def __init__(self, *args, **kwargs):
        # *args/**kwargs rather than restating BaseATSHandler's 13-parameter
        # signature: this adds state, it doesn't change the contract.
        super().__init__(*args, **kwargs)
        # Index of the section currently being filled (1-based once the loop
        # starts), and whether the last _advance_to_next_page() clicked Next
        # but the form stayed put.
        self._page_index = 0
        self._advance_blocked = False

    def _enter_application_flow(self):
        # Google Forms links go directly to the form -- there's no separate
        # "Apply" button/landing page to click through, unlike ATS postings.
        pass

    def _detect_and_set_iframe(self):
        # Google Forms are never embedded in an iframe from the applicant's
        # perspective -- self.page already is the form.
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        # Google Forms have no ATS-standard name/email/phone fields --
        # anything like that is just an ordinary form item, handled by the
        # generic _extract_questions()/_interact_widget() cycle instead.
        return True

    def _upload_resume(self) -> bool:
        # Only present if the form owner explicitly added a native file-
        # upload item; that item will show up in _extract_questions() as an
        # ordinary (if currently unhandled) widget_type, so there's nothing
        # to do at this fixed pipeline stage.
        return True

    def read_form_description(self):
        """JD-enrichment fallback step 2 (spec §2/§C) -- read once while the
        handler already has the form open, at zero extra API cost."""
        try:
            text = self.active_context.locator('div[role="heading"]').first.text_content()
            return text.strip() if text else None
        except Exception as e:
            logger.info(f"[GoogleFormsHandler] could not read form description: {e}")
            return None

    def _extract_questions(self) -> list:
        """Extracts questions for the CURRENT page/section only -- Google
        Forms sections are separate DOM subtrees that only exist once
        you've navigated to them via _advance_to_next_page()."""
        questions = []
        items = self.active_context.locator('div[role="listitem"]').all()
        for item in items:
            label_el = item.locator('div[role="heading"]').first
            raw_label = label_el.text_content() or ""
            is_required = "*" in raw_label
            clean_label = raw_label.replace("*", "").strip()

            widget_type = "input"
            options = []
            if item.get_by_role("button", name=re.compile("add file", re.I)).count() > 0:
                # Google Forms' native file-upload question opens a real
                # Google Drive picker dialog -- not something this handler
                # can drive (no Drive auth context, no stable DOM to
                # automate against). Tagging it "file_upload" rather than
                # letting it fall through to "input" matters: "input" would
                # have QuestionEngine type a text answer into what's
                # actually an upload button, silently mis-answering instead
                # of failing safely. _interact_widget (base_handler.py) has
                # no case for "file_upload", so it naturally no-ops via
                # _interact_custom_dropdown's default False return --
                # file-upload questions surface as a failed interaction
                # (REVIEW_REQUIRED) instead of a fabricated answer.
                #
                # Note this blocks submission for ANY file-upload question,
                # required or optional -- unlike the unanswerable/escalated
                # paths in _process_custom_fields, which skip optional
                # questions and continue. That's because the block happens at
                # the *interaction* stage (a False from _interact_widget sets
                # safe_to_submit = False unconditionally, base_handler.py:402-405),
                # which never consults is_required. Deliberate: an application
                # that silently skipped the resume attachment is worse than one
                # that asks a human to finish it, and a form owner who added an
                # upload item almost always wants the file.
                widget_type = "file_upload"
            else:
                for role, mapped in _WIDGET_TYPE_BY_ROLE.items():
                    role_items = item.get_by_role(role).all()
                    if role_items:
                        widget_type = mapped
                        options = [el.get_attribute("aria-label") or el.text_content() or "" for el in role_items]
                        break
                else:
                    if item.locator("textarea").count() > 0:
                        widget_type = "textarea"

            questions.append({
                "container": item,
                "question": clean_label,
                "raw_label": raw_label,
                "is_required": is_required,
                "widget_type": widget_type,
                "options": options,
                "placeholder": "",
            })
        return questions

    # ------------------------------------------------------------------
    # ARIA widget interaction
    #
    # base_handler._interact_widget drives native HTML: `container.locator("select")
    # .select_option()` for native_select, and `container.locator("label")` ->
    # nested `input` -> `.click()` + `.is_checked()` for radio/checkbox groups.
    # A Google Form has none of those elements, so every dropdown, multiple-
    # choice and checkbox question either raised or returned False -- which is
    # safe (it forces REVIEW_REQUIRED) but means only pure short-answer forms
    # ever got filled end to end.
    # ------------------------------------------------------------------

    @staticmethod
    def _option_text(el) -> str:
        """Google labels each option with aria-label; text_content is the
        visible fallback for options that don't carry one."""
        try:
            label = el.get_attribute("aria-label")
        except Exception:
            label = None
        if label:
            return label.strip()
        try:
            return (el.text_content() or "").strip()
        except Exception:
            return ""

    @classmethod
    def _find_option(cls, elements, answer: str):
        """Exact label match across ALL options first, substring only as a
        fallback. A single-pass "first element that contains the answer" would
        pick "Yes, with sponsorship" over the literal "Yes" purely because it
        comes first in the DOM -- on a knockout question that's a wrong answer,
        not a near miss."""
        wanted = (answer or "").strip().lower()
        if not wanted:
            return None
        labels = [(el, cls._option_text(el).lower()) for el in elements]
        for el, text in labels:
            if text and text == wanted:
                return el
        for el, text in labels:
            if text and wanted in text:
                return el
        return None

    @classmethod
    def _matches(cls, el, answer: str) -> bool:
        text = cls._option_text(el).lower()
        wanted = (answer or "").strip().lower()
        if not text or not wanted:
            return False
        return text == wanted or wanted in text

    @staticmethod
    def _is_checked(el) -> bool:
        try:
            return (el.get_attribute("aria-checked") or "").lower() == "true"
        except Exception:
            return False

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        # Route only the three ARIA-backed types away from the base class's
        # native-HTML implementation; input/textarea/file_upload behave
        # normally and must keep using the shared code path.
        if widget_type in _ARIA_ROLE_BY_WIDGET_TYPE:
            interaction["Widget Type"] = widget_type
            return self._interact_custom_dropdown(container, answer, interaction)
        return super()._interact_widget(widget_type, container, answer, interaction)

    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        widget_type = interaction.get("Widget Type", "")
        if widget_type == "native_select":
            return self._select_from_aria_listbox(container, answer, interaction)
        if widget_type in ("radio_group", "checkbox_group"):
            return self._toggle_aria_options(container, answer, interaction, widget_type)
        return False

    def _select_from_aria_listbox(self, container, answer: str, interaction: dict) -> bool:
        """Google's dropdown is a `div[role=listbox]` whose `div[role=option]`
        children are only clickable once the listbox has been opened."""
        interaction["Selector Used"] = 'div[role="listbox"] -> div[role="option"]'
        interaction["Interaction Method"] = "click() (ARIA listbox)"

        listbox = container.locator('div[role="listbox"]').first
        try:
            listbox.click(timeout=3000)
        except Exception as e:
            logger.info(f"GoogleFormsHandler: could not open listbox: {e}")
            return False
        self.page.wait_for_timeout(200)

        # Options can be reparented to a popup outside the question container
        # when the listbox opens, so fall back to a page-wide search before
        # giving up.
        for scope in (container, self.active_context):
            try:
                options = scope.locator('div[role="option"]').all()
            except Exception:
                continue
            opt = self._find_option(options, answer)
            if opt is None:
                continue
            try:
                opt.click(timeout=3000)
            except Exception as e:
                logger.info(f"GoogleFormsHandler: could not click option '{answer}': {e}")
                return False
            self.page.wait_for_timeout(150)
            return True

        logger.info(f"GoogleFormsHandler: no listbox option matching '{answer}'")
        return False

    def _toggle_aria_options(self, container, answer: str, interaction: dict, widget_type: str) -> bool:
        """Clicks the `div[role=radio]` / `div[role=checkbox]` element(s)
        matching the answer and verifies via aria-checked.

        QuestionEngine returns a single option string even for a multiselect
        (question_engine.py:496 -- it picks one of `options` or bails with
        REVIEW_REQUIRED), so the single-value path is the normal one. A
        comma-joined answer is still honoured for checkbox groups, but only
        when EVERY comma-separated part matches a real option -- otherwise the
        commas belong to the option's own text and splitting would match
        nothing."""
        role = _ARIA_ROLE_BY_WIDGET_TYPE[widget_type]
        interaction["Selector Used"] = f'div[role="{role}"]'
        interaction["Interaction Method"] = "click() (ARIA option)"

        try:
            elements = container.locator(f'div[role="{role}"]').all()
        except Exception as e:
            logger.info(f"GoogleFormsHandler: could not enumerate {role} options: {e}")
            return False
        if not elements:
            return False

        wanted = [answer]
        if widget_type == "checkbox_group" and "," in answer:
            parts = [p.strip() for p in answer.split(",") if p.strip()]
            if len(parts) > 1 and all(any(self._matches(el, p) for el in elements) for p in parts):
                wanted = parts

        clicked_any = False
        for want in wanted:
            target = self._find_option(elements, want)
            if target is None:
                logger.info(f"GoogleFormsHandler: no {role} option matching '{want}'")
                return False
            if self._is_checked(target):
                # Already in the desired state (radio pre-selected by the form
                # owner, or a checkbox this loop just set) -- clicking again
                # would toggle it back off.
                clicked_any = True
                continue
            try:
                target.click(timeout=3000)
            except Exception as e:
                logger.info(f"GoogleFormsHandler: could not click {role} option '{want}': {e}")
                return False
            self.page.wait_for_timeout(150)
            if not self._is_checked(target):
                logger.info(f"GoogleFormsHandler: {role} option '{want}' did not become checked")
                return False
            clicked_any = True

        return clicked_any

    def _custom_field_is_empty(self, container, widget_type: str):
        """base_handler._pre_submit_audit checks radio/checkbox groups via
        `container.locator("input").is_checked()` and dropdowns via
        `container.locator("select").input_value()`. Neither element exists in
        a Google Form, so the audit would report every correctly-filled
        multiple-choice question as empty (and every dropdown as filled).
        Answer from the ARIA state instead."""
        role = _ARIA_ROLE_BY_WIDGET_TYPE.get(widget_type)
        if role is None:
            return None
        try:
            if widget_type == "native_select":
                options = container.locator('div[role="option"]').all()
                return not any(
                    (o.get_attribute("aria-selected") or "").lower() == "true" for o in options
                )
            return not any(self._is_checked(el) for el in container.locator(f'div[role="{role}"]').all())
        except Exception as e:
            logger.info(f"GoogleFormsHandler: could not audit {widget_type}: {e}")
            # None defers to the generic check, which would false-positive
            # here; True ("empty") would block every submission on a DOM read
            # hiccup. False is the least-bad: the interaction result already
            # gates safe_to_submit for anything this handler actually filled.
            return False

    # ------------------------------------------------------------------
    # Multi-section support
    # ------------------------------------------------------------------

    def _process_custom_fields(self, telemetry: dict) -> bool:
        """Fills EVERY section of the form, not just the one on screen.

        base_handler.execute() calls this exactly once per retry cycle and
        then goes straight to the pre-submit audit and the submit click. On
        a sectioned Google Form that would fill section 1, then look for a
        Submit button that isn't rendered yet -- sections 2..n would never
        be seen at all. So the per-section walk lives here, inside the one
        hook execute() already calls once per form: each iteration delegates
        to the base implementation (classification, answering, widget
        interaction, telemetry -- all unchanged) for the section currently
        in the DOM, then clicks Next and repeats. execute() itself is
        untouched, which matters because all 15 other handlers share it.

        Stops early, unsafe, if a section couldn't be filled -- there's no
        point clicking Next when we already know the form is going to
        REVIEW_REQUIRED, and Google Forms would refuse to advance anyway.
        """
        safe_to_submit = True
        self._page_index = 0

        while self._page_index < self._MAX_FORM_SECTIONS:
            self._page_index += 1
            logger.info(f"GoogleFormsHandler: Filling form section {self._page_index}...")

            if not super()._process_custom_fields(telemetry):
                safe_to_submit = False
                break

            # execute() runs _pre_submit_audit() once, after this whole walk
            # has finished -- by which point sections 1..n-1 are no longer in
            # the DOM, so the audit only ever saw the LAST section. Every
            # earlier section's required fields went unaudited by this
            # codebase (Google's own Next-button validation partially covers
            # it via _advance_blocked, but that's Google's check, not ours).
            # Audit each section while it's still on screen, and remember a
            # failure for the whole walk even if later sections look clean.
            if not self._pre_submit_audit():
                logger.info(f"GoogleFormsHandler: Section {self._page_index} failed the pre-submit audit.")
                telemetry.setdefault("missing_fields", []).append({
                    "type": "SECTION_AUDIT_FAILED",
                    "question": f"(section {self._page_index}) empty required field(s) detected",
                    "confidence": 0,
                    "required": True,
                })
                safe_to_submit = False

            if not self._advance_to_next_page():
                if self._advance_blocked:
                    # Google Forms itself rejected the Next click, which it
                    # only does when a required question on this section is
                    # still empty -- i.e. the form is genuinely incomplete,
                    # even though every question we recognized was answered.
                    logger.info("GoogleFormsHandler: Form refused to advance past this section (unfilled required question). REVIEW_REQUIRED.")
                    telemetry.setdefault("missing_fields", []).append({
                        "type": "SECTION_ADVANCE_BLOCKED",
                        "question": f"(section {self._page_index}) form would not advance past this section",
                        "confidence": 0,
                        "required": True,
                    })
                    safe_to_submit = False
                # Otherwise: no Next button at all -- this was the final
                # section, and execute() can proceed to audit and submit it.
                break
        else:
            logger.info(f"GoogleFormsHandler: Hit the {self._MAX_FORM_SECTIONS}-section cap without reaching a final section. REVIEW_REQUIRED.")
            safe_to_submit = False

        telemetry["form_sections_processed"] = self._page_index
        return safe_to_submit

    def _current_section_fingerprint(self) -> str:
        """Cheap identity for whichever section is currently rendered, used
        only to tell "Next actually moved us" apart from "Next was rejected".
        Deliberately not _extract_questions() -- this must stay a couple of
        DOM reads, not a full re-parse of every question on the page."""
        try:
            items = self.active_context.locator('div[role="listitem"]')
            count = items.count()
            heading = ""
            if count:
                heading = items.first.locator('div[role="heading"]').first.text_content() or ""
            return f"{count}::{heading.strip()}"
        except Exception as e:
            logger.info(f"GoogleFormsHandler: could not fingerprint current section: {e}")
            return ""

    def _advance_to_next_page(self) -> bool:
        """Clicks Google Forms' "Next" button if this section has one.
        Returns False when there's no Next button left (i.e. this was the
        final section, with only Submit remaining) AND when a Next button
        was clicked but the form stayed on the same section -- the caller
        tells those two apart via self._advance_blocked, because only the
        second one means something went wrong."""
        self._advance_blocked = False
        next_button = self.active_context.get_by_role("button", name="Next")
        if next_button.count() == 0:
            return False

        before = self._current_section_fingerprint()
        next_button.first.click()
        self.active_context.wait_for_timeout(500)

        if self._current_section_fingerprint() == before:
            # Next is still there and the questions didn't change: Google
            # Forms blocked the transition (its own required-question
            # validation) rather than us mis-reading the DOM.
            self._advance_blocked = True
            return False
        return True

    def _get_submit_button_locator(self):
        return self.active_context.get_by_role("button", name="Submit")
