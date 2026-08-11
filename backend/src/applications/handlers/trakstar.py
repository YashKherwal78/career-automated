from src.system.logger import setup_logger
logger = setup_logger('trakstar')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class TrakstarHandler(BaseATSHandler):
    """
    Trakstar Hire (formerly Recruiterbox, <tenant>.hire.trakstar.com)
    postings render the application form directly on the job page, either
    already visible or revealed in-place by clicking "Apply" (no
    navigation, no iframe). The simplest DOM of any platform built this
    session: every field, standard and custom, is a plain native
    input/textarea/select with a real `<label for="id_...">` — no custom
    combobox widgets anywhere. Custom questions are tenant-authored and
    their field `name` is a slugified version of the full question text.
    A standard (invisible-mode) reCAPTCHA badge is present, already
    covered by the shared base_handler pause/resume mechanism.
    """
    ATS_NAME = "TRAKSTAR"

    _STANDARD_NAMES = {"candidate_first_name", "candidate_last_name", "candidate_email", "candidate_phone", "resume"}

    def _enter_application_flow(self):
        logger.info("TrakstarHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('#id_candidate_first_name', timeout=2000)
            if self.page.locator('#id_candidate_first_name').first.is_visible():
                return
        except Exception:
            pass
        try:
            apply_btn = self.page.get_by_role("link", name="Apply", exact=True).first
            if apply_btn.count() == 0:
                apply_btn = self.page.get_by_role("button", name="Apply", exact=True).first
            apply_btn.click(timeout=8000)
            self.page.wait_for_selector('#id_candidate_first_name', timeout=10000)
        except Exception as e:
            logger.info(f"TrakstarHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("TrakstarHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "candidate_first_name": self.profile.get_field("first_name"),
            "candidate_last_name": self.profile.get_field("last_name"),
            "candidate_email": self.profile.get_field("email"),
            "candidate_phone": self.profile.get_field("phone"),
        }
        for name, val in fields.items():
            if not val:
                continue
            el = self.active_context.locator(f'input[name="{name}"]').first
            if el.count() == 0:
                continue
            try:
                self._human_type(el, val)
                self.page.wait_for_timeout(150)
                if not el.input_value():
                    logger.info(f"TrakstarHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif name == "candidate_email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif name == "candidate_phone":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"TrakstarHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"TrakstarHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('input[name="resume"]').first
        if file_input.count() == 0:
            file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("TrakstarHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"TrakstarHandler: set_input_files failed: {e}")
            return False

        # This is a genuinely native, unstyled <input type="file"> ("Choose
        # File | No file chosen") — the "chosen filename" text Chromium
        # renders is native browser form-control UI, not real page DOM/
        # text content, so a text= locator search can never find it here
        # (same root cause as the JazzHR resume-upload bug earlier this
        # session). Check the input's own .files property directly.
        try:
            has_file = file_input.evaluate("el => el.files && el.files.length > 0")
        except Exception:
            has_file = False
        if not has_file:
            logger.info("  -> Upload Verified: False (Could not verify DOM)")
            self._capture_screenshot("resume_verification_failure.png")
            return False
        logger.info("  -> Upload Verified: True (input.files populated)")

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("TrakstarHandler: Extracting custom questions...")
        questions = []
        labels = self.active_context.locator("label[for]").all()

        for label_loc in labels:
            try:
                if not label_loc.is_visible():
                    continue
                for_id = label_loc.get_attribute("for") or ""
                name = for_id.replace("id_", "", 1)
                if name in self._STANDARD_NAMES:
                    continue

                target = self.active_context.locator(f'#{for_id}').first
                if target.count() == 0:
                    continue
                typ = (target.get_attribute("type") or "").lower()
                if typ == "file":
                    continue

                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue
                is_required = "*" in label_loc.inner_text()

                tag = target.evaluate("e => e.tagName").lower()
                widget_type = "unknown"
                options = []
                placeholder = target.get_attribute("placeholder") or ""

                if tag == "select":
                    widget_type = "native_select"
                    options = [o.strip() for o in target.locator("option").all_inner_texts() if o.strip()]
                elif tag == "textarea":
                    widget_type = "textarea"
                elif typ == "checkbox":
                    widget_type = "checkbox_group"
                elif typ == "radio":
                    widget_type = "radio_group"
                elif typ not in ("hidden",):
                    widget_type = "input"

                if widget_type == "unknown":
                    continue

                questions.append({
                    "container": target, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"TrakstarHandler: Detected {len(questions)} custom questions.")
        return questions

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        # Labels are linked via `for`, not by wrapping the field, so
        # "container" here is always the raw input/select/textarea itself.
        try:
            if widget_type == "native_select":
                interaction["Selector Used"] = "select (direct)"
                interaction["Interaction Method"] = "select_option"
                try:
                    container.select_option(label=answer)
                except Exception:
                    container.select_option(value=answer)
                container.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
                return True

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
            if widget_type == "checkbox_group":
                return not container.is_checked()
            return not container.input_value().strip()
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
