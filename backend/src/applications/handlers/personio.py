from src.system.logger import setup_logger
logger = setup_logger('personio')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class PersonioHandler(BaseATSHandler):
    """
    Personio postings (<tenant>.jobs.personio.com/job/<id>) render the
    application form directly on the job page once "Apply for this job"
    is clicked (URL just gains a `?apply` query param, no navigation).
    Clean, no captcha, no account required on every posting scouted.

    Every field has a real `<label for="field-<key>">`, and that `<key>`
    matches the input's own `name` attribute directly — standard fields
    use stable names (`first_name`, `last_name`, `email`, `phone`,
    `documents.cv`, `documents.other`); tenant-configured fields (a
    LinkedIn URL, or genuine custom screening questions) use
    `custom_attribute_<id>` instead, with the real prompt only ever
    available via that label text.
    """
    ATS_NAME = "PERSONIO"

    _STANDARD_KEYS = {"first_name", "last_name", "email", "phone", "documents.cv", "documents.other"}

    def _enter_application_flow(self):
        logger.info("PersonioHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('input[name="first_name"]', timeout=2000)
            return
        except Exception:
            pass
        try:
            apply_link = self.page.get_by_text("Apply for this job", exact=False).first
            apply_link.click(timeout=8000)
            self.page.wait_for_selector('input[name="first_name"]', timeout=10000)
        except Exception as e:
            logger.info(f"PersonioHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("PersonioHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "first_name": self.profile.get_field("first_name"),
            "last_name": self.profile.get_field("last_name"),
            "email": self.profile.get_field("email"),
            "phone": self.profile.get_field("phone"),
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
                    logger.info(f"PersonioHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif name == "email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif name == "phone":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"PersonioHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"PersonioHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('input[name="documents.cv"]').first
        if file_input.count() == 0:
            file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("PersonioHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"PersonioHandler: set_input_files failed: {e}")
            return False

        resume_base = os.path.splitext(os.path.basename(self.resume_path))[0]
        try:
            self.active_context.wait_for_selector(f"text={resume_base}", timeout=8000)
            logger.info("  -> Upload Verified: True")
        except Exception:
            logger.info("  -> Upload Verified: False (Could not verify DOM)")
            self._capture_screenshot("resume_verification_failure.png")
            return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("PersonioHandler: Extracting custom questions...")
        questions = []
        labels = self.active_context.locator('label[for^="field-"]').all()

        for label_loc in labels:
            try:
                if not label_loc.is_visible():
                    continue
                for_id = label_loc.get_attribute("for") or ""
                key = for_id.replace("field-", "", 1)
                if key in self._STANDARD_KEYS:
                    continue

                target = self.active_context.locator(f'[name="{key}"]').first
                if target.count() == 0:
                    continue
                if target.get_attribute("type") == "file":
                    continue

                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue
                is_required = "*" in raw_text or "(required)" in label_loc.inner_text().lower()

                tag = target.evaluate("e => e.tagName").lower()
                typ = (target.get_attribute("type") or "").lower()
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

        logger.info(f"PersonioHandler: Detected {len(questions)} custom questions.")
        return questions

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        # _extract_questions() passes the raw input/select/textarea itself
        # as "container" (labels are linked by `for`, not by wrapping the
        # field), so the base class's container.locator(...) descendant
        # search never finds anything — interact with the element directly.
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
            if widget_type == "native_select":
                return not container.input_value()
            return not container.input_value().strip()
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
