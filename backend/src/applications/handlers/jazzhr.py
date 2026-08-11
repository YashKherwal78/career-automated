from src.system.logger import setup_logger
logger = setup_logger('jazzhr')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class JazzHRHandler(BaseATSHandler):
    """
    JazzHR (product name "Resumator") postings are hosted on
    <tenant>.applytojob.com. The apply form is hidden on the job-detail
    page until an "apply now" link is clicked, then reveals a plain HTML
    form with no <label> tags at all — every field instead follows one
    consistent, id-based convention:
        <div id="resumator-<key>" class="resumator-field-wrapper ...">
          <div id="resumator-<key>-label">Visible Label Text</div>
          <div id="resumator-<key>-field"><input name="resumator-<key>-value" ...></div>
        </div>
    which is what both the standard-field filling and the custom-question
    extractor below key off, instead of guessing at DOM structure per
    posting. A visible reCAPTCHA checkbox widget ("Human Check") gates
    submission — the shared base_handler CAPTCHA pause/resume mechanism
    already covers this (same category as Lever's hCaptcha: a real,
    solvable, visible challenge, not a silent/invisible one).
    """
    ATS_NAME = "JAZZHR"

    _SKIP_KEYS = {"resume", "recaptcha", "submit", "message", "resumes"}

    def _enter_application_flow(self):
        logger.info("JazzHRHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('input[name="resumator-firstname-value"]', timeout=3000)
            return
        except Exception:
            pass
        try:
            apply_link = self.page.get_by_text(re.compile("apply now", re.I)).first
            apply_link.click(timeout=5000)
            self.page.wait_for_selector('input[name="resumator-firstname-value"]', timeout=10000)
        except Exception as e:
            logger.info(f"JazzHRHandler: Apply-link click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("JazzHRHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "resumator-firstname-value": self.profile.get_field("first_name"),
            "resumator-lastname-value": self.profile.get_field("last_name"),
            "resumator-email-value": self.profile.get_field("email"),
            "resumator-phone-value": self.profile.get_field("phone"),
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
                    logger.info(f"JazzHRHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif "email" in name:
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif "phone" in name:
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"JazzHRHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        # Optional Location sub-fields (Address/City/State/Postal).
        optional_fields = {
            "resumator-address-value": self.profile.get_field("address"),
            "resumator-city-value": self.profile.get_field("city"),
            "resumator-state-value": self.profile.get_field("state"),
        }
        for name, val in optional_fields.items():
            if not val:
                continue
            el = self.active_context.locator(f'input[name="{name}"]').first
            if el.count() > 0:
                try:
                    self._human_type(el, val)
                except Exception as e:
                    logger.info(f"JazzHRHandler: Error filling {name} (non-fatal): {e}")

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"JazzHRHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        # The real file input starts hidden — clicking the "Attach resume"
        # link is what makes it visible/active and wires up the JS that
        # renders the selected filename afterward. Setting files on the
        # still-hidden input silently no-ops (no error, but nothing renders
        # and the field stays functionally empty).
        try:
            attach_link = self.active_context.get_by_text("Attach resume", exact=False).first
            if attach_link.count() > 0 and attach_link.is_visible():
                attach_link.click(timeout=3000)
                self.page.wait_for_timeout(500)
        except Exception as e:
            logger.info(f"JazzHRHandler: 'Attach resume' click skipped/failed (non-fatal): {e}")

        file_input = self.active_context.locator('input[name="resumator-resume-value"], input[type="file"]').first
        if file_input.count() == 0:
            logger.info("JazzHRHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"JazzHRHandler: set_input_files failed: {e}")
            return False

        # This is a genuinely native, unstyled <input type="file"> — the
        # "chosen filename" text Chromium renders next to it is native
        # browser form-control UI, not real page text/DOM content, so a
        # text= locator search (which works for every other handler's
        # styled upload widgets) can never find it here. Check the input's
        # own .files property directly instead.
        try:
            has_file = file_input.evaluate("el => el.files && el.files.length > 0")
        except Exception:
            has_file = False
        if has_file:
            logger.info("  -> Upload Verified: True (input.files populated)")
        else:
            logger.info("  -> Upload Verified: False (Could not verify DOM)")
            self._capture_screenshot("resume_verification_failure.png")
            return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("JazzHRHandler: Extracting custom questions...")
        questions = []
        wrappers = self.active_context.locator('div.resumator-field-wrapper[id^="resumator-"]').all()

        for wrapper in wrappers:
            try:
                if not wrapper.is_visible():
                    continue
                wrapper_id = wrapper.get_attribute("id") or ""
                key = wrapper_id.replace("resumator-", "", 1)
                if key in self._SKIP_KEYS or key in (
                    "firstname", "lastname", "email", "phone", "address"
                ):
                    continue

                label_loc = wrapper.locator(f'#{wrapper_id}-label, .resumator-label').first
                if label_loc.count() == 0:
                    continue
                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue

                field_container = wrapper.locator(f'#{wrapper_id}-field').first
                if field_container.count() == 0:
                    field_container = wrapper
                if field_container.locator('input[type="file"]').count() > 0:
                    continue

                is_required = "*" in raw_text

                options = []
                widget_type = "unknown"
                placeholder = ""

                radios = field_container.locator('input[type="radio"]')
                checkboxes = field_container.locator('input[type="checkbox"]')

                if field_container.locator("select").count() > 0:
                    widget_type = "native_select"
                    options = [o.strip() for o in field_container.locator("option").all_inner_texts() if o.strip()]
                elif radios.count() > 0 or checkboxes.count() > 0:
                    widget_type = "radio_group" if radios.count() > 0 else "checkbox_group"
                    labels = field_container.locator("label").all_inner_texts()
                    options = [l.strip() for l in labels if l.strip()]
                elif field_container.locator("textarea").count() > 0:
                    widget_type = "textarea"
                    ph = field_container.locator("textarea").first.get_attribute("placeholder")
                    if ph: placeholder = ph
                elif field_container.locator('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"])').count() > 0:
                    widget_type = "input"
                    ph = field_container.locator("input").first.get_attribute("placeholder")
                    if ph: placeholder = ph

                questions.append({
                    "container": field_container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"JazzHRHandler: Detected {len(questions)} custom questions.")
        return questions

    def _get_submit_button_locator(self):
        return self.page.locator('#resumator-submit-resume, input[name="submit_resume"]').first
