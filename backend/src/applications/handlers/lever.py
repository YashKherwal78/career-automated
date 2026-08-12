from src.system.logger import setup_logger
logger = setup_logger('lever')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class LeverHandler(BaseATSHandler):
    """
    Lever application forms are plain HTML (native <select>, native
    radio/checkbox), not a React widget library like Greenhouse — so this
    handler needs no _interact_custom_dropdown override, and the shared
    base's generic widget interaction covers everything. The apply URL
    Lever hands out already points straight at the form (no "Apply" click
    or iframe involved), and anti-bot here is hCaptcha, not reCAPTCHA.
    """
    ATS_NAME = "LEVER"

    def _enter_application_flow(self):
        logger.info("LeverHandler: Entering application flow...")
        # Lever job postings today are a JD landing page with a separate
        # "Apply for this job" link (pointing at a `/apply`-suffixed URL) —
        # the form itself isn't on the page until that's clicked/navigated.
        try:
            self.page.wait_for_selector(".application-question, input[type='file']", timeout=3000)
            return
        except Exception:
            pass

        try:
            apply_link = self.page.get_by_role("link", name=re.compile("apply for this job", re.I)).first
            apply_link.click(timeout=5000)
            self.page.wait_for_selector(".application-question, input[type='file']", timeout=10000)
        except Exception as e:
            logger.info(f"LeverHandler: Apply-link click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        # Lever's form renders directly in the main page — no iframe hop needed.
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("LeverHandler: Verifying standard fields...")
        safe_to_proceed = True

        full_name = f"{self.profile.get_field('first_name') or ''} {self.profile.get_field('last_name') or ''}".strip()
        fields = {
            "name": full_name,
            "email": self.profile.get_field("email"),
            "phone": self.profile.get_field("phone"),
        }

        for key, val in fields.items():
            if not val:
                continue
            input_el = self.active_context.locator(f'input[name="{key}"]').first
            if input_el.count() == 0:
                continue
            try:
                self._human_type(input_el, val)
                self.page.wait_for_timeout(150)
                if not input_el.input_value():
                    logger.info(f"LeverHandler: CRITICAL - Field {key} failed to populate.")
                    safe_to_proceed = False
                elif key == "email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif key == "phone":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"LeverHandler: Error filling {key}: {e}")
                safe_to_proceed = False

        # "Current location" is a free-text + autocomplete field. Fill the
        # text and try to accept the first suggestion; if none appears
        # (some tenants accept free text directly) the typed value stands.
        location = self.profile.get_field("current_location") or self.profile.get_field("location")
        loc_input = self.active_context.locator("#location-input, input[name='location']").first
        if location and loc_input.count() > 0:
            try:
                # Human-paced typing (real keystrokes, not one instant value
                # set) also happens to matter functionally here, not just
                # for realism — this autocomplete only populates suggestions
                # in response to real input events per character.
                self._human_type(loc_input, location)
                self.page.wait_for_timeout(600)
                suggestion = self.active_context.locator('[class*="suggestion"], li[role="option"]').first
                if suggestion.count() > 0 and suggestion.is_visible():
                    suggestion.click(timeout=2000)
            except Exception as e:
                logger.info(f"LeverHandler: Location autocomplete error (non-fatal): {e}")

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"LeverHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        # Lever's application form is a React SPA — the file input can mount
        # after the rest of the form is visible (same race Greenhouse hit
        # and was fixed for in commit 71bc99d: absent at 1.5s, present by
        # 4s there). This had no wait at all, so a slow mount meant
        # count() == 0 and an immediate, unretried give-up.
        try:
            self.active_context.wait_for_selector(
                'input[type="file"][name="resume"], #resume-upload-input, input[type="file"]',
                timeout=8000,
            )
        except Exception:
            pass

        file_input = self.active_context.locator('input[type="file"][name="resume"], #resume-upload-input, input[type="file"]').first
        if file_input.count() == 0:
            logger.info("LeverHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"LeverHandler: set_input_files failed: {e}")
            return False

        resume_base = os.path.splitext(os.path.basename(self.resume_path))[0]
        try:
            self.active_context.wait_for_selector(f"text={resume_base}", timeout=8000)
            logger.info("  -> Upload Verified: True")
        except Exception:
            try:
                self.active_context.wait_for_selector('text=/remove/i', timeout=4000)
                logger.info("  -> Upload Verified: True (via Remove link)")
            except Exception:
                logger.info("  -> Upload Verified: False (Could not verify DOM)")
                self._capture_screenshot("resume_verification_failure.png")
                return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("LeverHandler: Extracting questions...")
        questions = []
        containers = self.active_context.locator(".application-question").all()

        skip_list = ["full name", "name", "email", "phone", "resume/cv", "resume", "cv", "current location", "location"]

        for container in containers:
            try:
                if not container.is_visible():
                    continue
                label_loc = container.locator(".application-label .text, .application-label").first
                if label_loc.count() == 0:
                    continue
                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("✱", "").strip()
                if not clean_label or clean_label.lower() in skip_list:
                    continue

                is_required = container.locator(".required").count() > 0 or container.locator("[required]").count() > 0

                options = []
                widget_type = "unknown"
                placeholder = ""

                radios = container.locator('input[type="radio"]')
                checkboxes = container.locator('input[type="checkbox"]')

                if container.locator("select").count() > 0:
                    widget_type = "native_select"
                    options = [o.strip() for o in container.locator("option").all_inner_texts() if o.strip() and "select" not in o.lower()]
                elif radios.count() > 0 or checkboxes.count() > 0:
                    widget_type = "radio_group" if radios.count() > 0 else "checkbox_group"
                    alt_labels = container.locator(".application-answer-alternative").all_inner_texts()
                    options = [l.strip() for l in alt_labels if l.strip()]
                elif container.locator("textarea").count() > 0:
                    widget_type = "textarea"
                    ph = container.locator("textarea").first.get_attribute("placeholder")
                    if ph: placeholder = ph
                elif container.locator('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"])').count() > 0:
                    # Broad text-like match rather than a type allowlist —
                    # some fields (e.g. LinkedIn profile) render without an
                    # explicit `type` attribute at all, which an allowlist of
                    # text/email/tel/url misses, leaving the field
                    # "unknown" and silently unfilled (falls through to the
                    # base class's no-op custom-dropdown handler).
                    widget_type = "input"
                    ph = container.locator("input").first.get_attribute("placeholder")
                    if ph: placeholder = ph

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"LeverHandler: Detected {len(questions)} questions.")
        return questions

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
