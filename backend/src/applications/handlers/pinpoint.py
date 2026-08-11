from src.system.logger import setup_logger
logger = setup_logger('pinpoint')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class PinpointHandler(BaseATSHandler):
    """
    Pinpoint postings (<tenant>.pinpointhq.com/en/postings/<uuid>) navigate
    to a genuine `/applications/new` page on "Apply now" — no iframe, no
    login. Standard fields use stable Rails-bracket names
    (`application_form[application][first_name]`, etc.) with real
    `<label for="application_form_application_first_name">` elements
    (brackets become underscores in the generated id).

    Two distinct dropdown widgets appear on every posting:
    - Country and the "Diversity and Inclusion" EEO fields are all the
      same `react-select` component (`.react-select__control` trigger +
      portaled `[role="option"]` list) — same interaction shape as
      Greenhouse's react-select.
    - Phone's country-code prefix is the classic `intl-tel-input` library
      instead — click `.selected-flag`, then click
      `li.country[data-country-code="<iso2>"]` directly, no search needed.
    """
    ATS_NAME = "PINPOINT"

    _STANDARD_NAMES = {
        "first_name", "last_name", "email", "phone", "phone_iso2", "country",
        "address1", "address2", "town", "postcode", "cv", "summary",
    }

    def _enter_application_flow(self):
        logger.info("PinpointHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('input[name="application_form[application][first_name]"]', timeout=2000)
            return
        except Exception:
            pass
        try:
            apply_btn = self.page.get_by_text("Apply now", exact=False).first
            apply_btn.click(timeout=8000)
            self.page.wait_for_selector('input[name="application_form[application][first_name]"]', timeout=10000)
        except Exception as e:
            logger.info(f"PinpointHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_text_field(self, key: str, value: str) -> bool:
        if not value:
            return True
        el = self.active_context.locator(f'input[name="application_form[application][{key}]"]').first
        if el.count() == 0:
            return True
        try:
            self._human_type(el, value)
            self.page.wait_for_timeout(150)
            return bool(el.input_value())
        except Exception as e:
            logger.info(f"PinpointHandler: Error filling {key}: {e}")
            return False

    def _select_react_option(self, wrapper, search_text: str) -> bool:
        try:
            control = wrapper.locator(".react-select__control").first
            control.click(timeout=5000)
            self.page.wait_for_timeout(400)
            self.page.keyboard.type(search_text, delay=100)
            self.page.wait_for_timeout(600)
            option = self.page.locator('[id*="-option-"]', has_text=re.compile(rf"^{re.escape(search_text)}$")).first
            if option.count() == 0:
                option = self.page.locator('[role="option"]', has_text=re.compile(rf"^{re.escape(search_text)}$")).first
            if option.count() == 0:
                # No exact match for this answer in this tenant's option
                # list (e.g. "Decline to Self Identify" isn't always the
                # exact wording used) — close the dropdown rather than
                # leave it open with stray typed search text sitting in
                # it, which corrupted a LATER retry-cycle attempt into
                # selecting a wrong, unintended option (observed live: an
                # Ethnicity field ended up set to "White British" after a
                # failed "Decline to Self Identify" search on an earlier
                # cycle). Never leave an optional demographic field with a
                # value that wasn't actually verified correct.
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(200)
                return False
            option.click(timeout=3000)
            self.page.wait_for_timeout(300)
            return True
        except Exception as e:
            logger.info(f"PinpointHandler: react-select interaction failed for '{search_text}': {e}")
            return False

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("PinpointHandler: Verifying standard fields...")
        safe_to_proceed = True

        safe_to_proceed &= self._fill_text_field("first_name", self.profile.get_field("first_name"))
        safe_to_proceed &= self._fill_text_field("last_name", self.profile.get_field("last_name"))
        if self._fill_text_field("email", self.profile.get_field("email")):
            self.telemetry.setdefault("filled_fields", {})["Email"] = True
        else:
            safe_to_proceed = False

        phone = self.profile.get_field("phone")
        phone_el = self.active_context.locator('input[name="application_form[application][phone]"]').first
        if phone and phone_el.count() > 0:
            try:
                self._human_type(phone_el, phone)
                if phone_el.input_value():
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"PinpointHandler: Error filling phone: {e}")

        # Phone country code (intl-tel-input) — a simple direct flag-list
        # click, not a searchable combobox like every other dropdown here.
        try:
            flag = self.active_context.locator(".selected-flag").first
            if flag.count() > 0:
                flag.click(timeout=5000)
                self.page.wait_for_timeout(400)
                li = self.active_context.locator('li.country[data-country-code="in"]').first
                if li.count() > 0:
                    li.click(timeout=3000)
        except Exception as e:
            logger.info(f"PinpointHandler: Phone country-code selection failed (non-fatal): {e}")

        # Country (react-select) must be set before address fields, same
        # ordering caution as every other platform with a similar widget.
        country_wrap = self.active_context.locator("#address-country").first
        if country_wrap.count() > 0:
            country = self.profile.get_field("country") or "India"
            if not self._select_react_option(country_wrap, country):
                logger.info("PinpointHandler: CRITICAL - Could not set Country.")
                safe_to_proceed = False

        safe_to_proceed &= self._fill_text_field("address1", self.profile.get_field("address"))
        safe_to_proceed &= self._fill_text_field("town", self.profile.get_field("city"))
        safe_to_proceed &= self._fill_text_field("postcode", self.profile.get_field("postal_code"))

        # Required data-processing consent checkbox, handled directly
        # rather than through the generic question pipeline — its actual
        # wording ("Allow us to process your personal information.")
        # doesn't contain "consent"/"privacy", the keywords the shared
        # LEGAL/PRIVACY_ACK classifier looks for, so it fell through to
        # the free-text LLM path and got a full sentence typed into a
        # checkbox instead of being checked. Same fixed "always consent"
        # treatment every other platform's own privacy checkbox gets.
        consent_el = self.active_context.locator("#application_process_information").first
        if consent_el.count() > 0:
            if not self._click_and_verify_checked(consent_el):
                logger.info("PinpointHandler: CRITICAL - Could not check required data-processing consent.")
                safe_to_proceed = False

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"PinpointHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('input[name="application_form[application][cv]"]').first
        if file_input.count() == 0:
            file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("PinpointHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"PinpointHandler: set_input_files failed: {e}")
            return False

        resume_base = os.path.splitext(os.path.basename(self.resume_path))[0]
        try:
            self.active_context.wait_for_selector(f"text={resume_base}", timeout=8000)
            logger.info("  -> Upload Verified: True")
        except Exception:
            try:
                self.active_context.wait_for_selector('text=/remove|delete/i', timeout=4000)
                logger.info("  -> Upload Verified: True (via Remove/Delete indicator)")
            except Exception:
                logger.info("  -> Upload Verified: False (Could not verify DOM)")
                self._capture_screenshot("resume_verification_failure.png")
                return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("PinpointHandler: Extracting custom questions...")
        questions = []
        labels = self.active_context.locator("label[for]").all()
        seen_radio_groups = set()

        for label_loc in labels:
            try:
                if not label_loc.is_visible():
                    continue
                for_id = label_loc.get_attribute("for") or ""
                if for_id == "application_process_information":
                    continue
                key = for_id.replace("application_form_application_", "", 1)
                if key in self._STANDARD_NAMES:
                    continue

                # Ethnicity's react-select on this platform doesn't offer a
                # "Decline to Self Identify"-equivalent option, and typing
                # a search string with no match doesn't just fail cleanly —
                # it lands on and COMMITS an unrelated, wrong option (live:
                # ended up selecting "White British", an outright false
                # statement about the candidate). No reliable way found to
                # clear a react-select back to empty afterward. Since this
                # is an optional demographic field, leaving it genuinely
                # unanswered is unambiguously safer than any auto-fill
                # attempt here — skip it outright rather than risk
                # submitting incorrect demographic data.
                if "equality_monitoring_ethnicity" in for_id.lower() or "equality_monitoring_race" in for_id.lower():
                    continue

                target = self.active_context.locator(f'#{for_id}').first
                if target.count() == 0:
                    continue

                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue
                is_required = "required" in (label_loc.get_attribute("class") or "").lower() or "*" in raw_text

                tag = target.evaluate("e => e.tagName").lower()
                typ = (target.get_attribute("type") or "").lower() if tag == "input" else ""

                widget_type = "unknown"
                options = []
                container = target

                # react-select (Country, every EEO field) renders its
                # label's `for` pointing at a hidden "dummy input"
                # (role=combobox, class containing "dummyInput") used only
                # for focus management — the real widget is an ANCESTOR
                # containing .react-select__control, not this element or
                # any descendant of it.
                if target.get_attribute("role") == "combobox" and "dummyinput" in (target.get_attribute("class") or "").lower():
                    react_wrap = target.locator("xpath=ancestor::div[3]").first
                    if react_wrap.count() > 0 and react_wrap.locator(".react-select__control").count() > 0:
                        widget_type = "pinpoint_select"
                        container = react_wrap
                elif typ == "radio":
                    group_name = target.get_attribute("name")
                    # Every radio in a group has its OWN <label for="...">
                    # pointing at just that one option — without dedup,
                    # each option in the group gets extracted as its own
                    # separate "question" (seen live: "Yes" and "No" both
                    # appeared as independent questions instead of one
                    # Yes/No radio_group).
                    if group_name in seen_radio_groups:
                        continue
                    seen_radio_groups.add(group_name)
                    widget_type = "radio_group"
                    radios = self.active_context.locator(f'input[name="{group_name}"]')
                    opt_labels = []
                    for i in range(radios.count()):
                        rid = radios.nth(i).get_attribute("id")
                        rlabel = self.active_context.locator(f'label[for="{rid}"]').first
                        if rlabel.count() > 0:
                            opt_labels.append(rlabel.inner_text().strip())
                    options = opt_labels
                    # "container" needs to wrap ALL options sharing this
                    # name, not just the single first input the label's
                    # `for` happens to point at.
                    container = self.active_context.locator(
                        f'xpath=(//input[@name="{group_name}"])[1]/ancestor::div[3]'
                    ).first
                elif typ == "checkbox":
                    widget_type = "checkbox_group"
                elif tag == "textarea":
                    widget_type = "textarea"
                elif typ not in ("hidden", "file"):
                    widget_type = "input"

                if widget_type == "unknown":
                    continue

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": "",
                })
            except Exception:
                pass

        logger.info(f"PinpointHandler: Detected {len(questions)} custom questions.")
        return questions

    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        interaction["Selector Used"] = ".react-select__control -> [role=option]"
        interaction["Interaction Method"] = "click() open, type(), click() option"
        return self._select_react_option(container, answer)

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        # For radio_group, "container" is a real wrapper (built above) so
        # the base class's own logic works unmodified. For input/textarea/
        # checkbox questions, "container" is the raw element itself since
        # labels are linked via `for`, not by wrapping — interact directly.
        if widget_type in ("radio_group", "pinpoint_select"):
            return super()._interact_widget(widget_type, container, answer, interaction)
        try:
            if widget_type == "checkbox_group" and answer.strip().rstrip(".").lower() in ("true", "yes"):
                return self._click_and_verify_checked(container)
            interaction["Selector Used"] = "input/textarea (direct)"
            interaction["Interaction Method"] = "type() (human-paced)"
            val = self._human_type(container, answer)
            if val != answer:
                interaction["Interaction Method"] = "fill() (typing fallback)"
                container.fill(answer)
                val = container.input_value()
            return val == answer
        except Exception:
            return super()._interact_widget(widget_type, container, answer, interaction)

    def _custom_field_is_empty(self, container, widget_type: str):
        try:
            if widget_type == "pinpoint_select":
                text = container.inner_text()
                return "select" in text.lower() and len(text.strip()) < 15
            if widget_type == "checkbox_group":
                return not container.is_checked()
            if widget_type == "radio_group":
                inputs = container.locator("input")
                return not any(inputs.nth(i).is_checked() for i in range(inputs.count()))
            return not container.input_value().strip()
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
