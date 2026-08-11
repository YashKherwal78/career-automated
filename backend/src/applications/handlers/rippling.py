from src.system.logger import setup_logger
logger = setup_logger('rippling')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class RipplingHandler(BaseATSHandler):
    """
    Rippling ATS postings (ats.rippling.com/<tenant>/jobs/<id>) hide the
    application form behind an "Apply now" click. Unlike most other
    platforms built this session, standard AND custom fields share one
    fully stable, semantic `data-testid` taxonomy regardless of tenant —
    `first_name`, `last_name`, `email`, `phone_number`, `location`,
    `linkedin_link`, `resume`, `cover_letter`, `eeoc.<field>`, and
    `customQuestions.<jobId>.<questionId>` — so field identification
    doesn't need the label-proximity guesswork other handlers required.
    Custom/EEO select-type questions render as an accessible
    `role="combobox"` + `role="option"` widget (real value has no plain
    input at all), same interaction shape as Greenhouse's react-select.
    """
    ATS_NAME = "RIPPLING"

    def _enter_application_flow(self):
        logger.info("RipplingHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('[data-testid="input-first_name"]', timeout=2000)
            return
        except Exception:
            pass
        try:
            apply_btn = self.page.get_by_text("Apply now", exact=False).first
            apply_btn.click(timeout=8000)
            self.page.wait_for_selector('[data-testid="input-first_name"]', timeout=10000)
        except Exception as e:
            logger.info(f"RipplingHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("RipplingHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "first_name": self.profile.get_field("first_name"),
            "last_name": self.profile.get_field("last_name"),
            "email": self.profile.get_field("email"),
            "phone_number": self.profile.get_field("phone"),
            "linkedin_link": self.profile.get_field("linkedin"),
        }
        for key, val in fields.items():
            if not val:
                continue
            el = self.active_context.locator(f'[data-testid="input-{key}"]').first
            if el.count() == 0:
                continue
            try:
                self._human_type(el, val)
                self.page.wait_for_timeout(150)
                if not el.input_value():
                    logger.info(f"RipplingHandler: CRITICAL - Field {key} failed to populate.")
                    safe_to_proceed = False
                elif key == "email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif key == "phone_number":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
                elif key == "linkedin_link":
                    self.telemetry.setdefault("filled_fields", {})["LinkedIn"] = True
            except Exception as e:
                logger.info(f"RipplingHandler: Error filling {key}: {e}")
                safe_to_proceed = False

        # Location: a Google-Places-style autocomplete. Free text alone
        # isn't accepted — a real suggestion must be clicked, and it needs
        # a full "City, Country"-shaped query and a couple seconds before
        # any suggestion renders.
        location = self.profile.get_field("current_location") or self.profile.get_field("city")
        loc_input = self.active_context.locator('[data-testid="location"] input').first
        if location and loc_input.count() > 0:
            try:
                loc_input.click(timeout=3000)
                loc_input.type(location, delay=120)
                self.page.wait_for_timeout(2000)
                suggestion = self.page.locator('[role="option"]').first
                if suggestion.count() > 0:
                    suggestion.click(timeout=3000)
                else:
                    logger.info("RipplingHandler: No location suggestion appeared (non-fatal, typed text left as-is).")
            except Exception as e:
                logger.info(f"RipplingHandler: Location autocomplete error (non-fatal): {e}")

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"RipplingHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('[data-testid="input-resume"]').first
        if file_input.count() == 0:
            file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("RipplingHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"RipplingHandler: set_input_files failed: {e}")
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
        logger.info("RipplingHandler: Extracting custom questions...")
        questions = []
        containers = self.active_context.locator(
            '[data-testid^="customQuestions."], [data-testid^="eeoc."]'
        ).all()

        for container in containers:
            try:
                testid = container.get_attribute("data-testid") or ""
                if testid.startswith("input-"):
                    continue
                if not container.is_visible():
                    continue

                options = []
                widget_type = "unknown"
                combobox = container.locator('[role="combobox"]').first
                if combobox.count() > 0:
                    widget_type = "rippling_select"
                elif container.locator("textarea").count() > 0:
                    widget_type = "textarea"
                elif container.locator('input:not([type="hidden"]):not([type="file"])').count() > 0:
                    widget_type = "input"

                if widget_type == "unknown":
                    continue

                # Combobox fields (both tenant custom questions and the
                # fixed EEO fields) expose their real label via
                # aria-labelledby -> a <span id="..."> elsewhere in the
                # DOM; that's the ONLY reliable source for EEO fields,
                # since a naive ancestor walk lands on the shared EEO
                # section's instructional paragraph instead of each
                # field's own short label ("Gender", "Please identify your
                # race", etc. all collapsed to the same wrong text
                # otherwise). Plain text-input custom questions don't set
                # aria-labelledby at all, so those fall back to the
                # nearest <p> a few levels up, which does hold the real
                # question text for that shape of field.
                raw_text = ""
                if widget_type == "rippling_select":
                    labelledby = combobox.get_attribute("aria-labelledby")
                    if labelledby:
                        label_el = self.page.locator(f"#{labelledby}").first
                        if label_el.count() > 0:
                            raw_text = label_el.inner_text().split("\n")[0].strip()
                if not raw_text:
                    ancestor = container.locator("xpath=ancestor::div[3]").first
                    p_tag = ancestor.locator("p").first
                    if p_tag.count() > 0:
                        raw_text = p_tag.inner_text().split("\n")[0].strip()
                clean_label = raw_text.strip()
                if not clean_label:
                    continue

                is_required = container.locator('[aria-required="true"]').count() > 0

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": "",
                })
            except Exception:
                pass

        logger.info(f"RipplingHandler: Detected {len(questions)} custom/EEO questions.")
        return questions

    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        """Rippling's accessible combobox: click to open, click the
        matching role=option (portaled to the page, not necessarily a
        DOM descendant of the field container by the time it's open)."""
        interaction["Selector Used"] = "[role=combobox] -> [role=option]"
        interaction["Interaction Method"] = "click() open, click() option"
        try:
            combo = container.locator('[role="combobox"]').first
            combo.click(timeout=5000)
            self.page.wait_for_timeout(500)
            option = self.page.locator('[role="option"]', has_text=answer).first
            if option.count() == 0:
                return False
            option.click(timeout=3000)
            self.page.wait_for_timeout(300)
            return True
        except Exception as e:
            logger.info(f"RipplingHandler: rippling_select interaction failed: {e}")
            return False

    def _custom_field_is_empty(self, container, widget_type: str):
        if widget_type != "rippling_select":
            return None
        try:
            combo_text = container.locator('[role="combobox"]').first.inner_text()
            return combo_text.strip().lower() in ("select", "")
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.locator('[data-testid="Apply"]').first
