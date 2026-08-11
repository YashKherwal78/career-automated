from src.system.logger import setup_logger
logger = setup_logger('workable')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class WorkableHandler(BaseATSHandler):
    """
    Workable postings live on apply.workable.com. A cookie-consent dialog
    renders as a full-screen overlay that intercepts every click until
    dismissed — must be cleared before "Apply for this job" is clickable
    at all. Every field (regardless of widget type) has a
    `span[id$="_label"]` sibling holding the visible question text; that
    id's non-"_label" prefix is stable for tenant-configured custom
    questions (e.g. "CA_4927") but randomly regenerated per page load for
    built-in boolean/text fields — so labels are matched by TEXT content,
    never by id, and the field's own container is found by walking up
    from the label to its first `<div>` ancestor (skips the label's own
    `<span>` wrappers, lands exactly on the one div containing just that
    field's widget(s) and nothing else).

    "Notice period"-style fields are a custom select: a real value only
    exists in a hidden input, driven by a `[data-input-type="select"]`
    wrapper that must be clicked open before its `[role="option"]` list
    exists in the DOM at all (same category as Greenhouse's react-select).
    """
    ATS_NAME = "WORKABLE"

    _STANDARD_LABELS = {"first name", "last name", "email", "phone", "resume"}

    def _enter_application_flow(self):
        logger.info("WorkableHandler: Entering application flow...")
        try:
            cookie_dialog = self.page.locator('[data-ui="cookie-consent"]').first
            if cookie_dialog.count() > 0 and cookie_dialog.is_visible():
                cookie_dialog.get_by_role("button", name="Accept", exact=False).first.click(timeout=5000)
                self.page.wait_for_timeout(500)
        except Exception as e:
            logger.info(f"WorkableHandler: Cookie consent dismiss skipped/failed (non-fatal): {e}")

        try:
            self.page.wait_for_selector('input[name="firstname"]', timeout=3000)
            return
        except Exception:
            pass
        try:
            apply_link = self.page.get_by_text("Apply for this job", exact=False).first
            apply_link.click(timeout=8000)
            self.page.wait_for_selector('input[name="firstname"]', timeout=10000)
        except Exception as e:
            logger.info(f"WorkableHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("WorkableHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "firstname": self.profile.get_field("first_name"),
            "lastname": self.profile.get_field("last_name"),
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
                    logger.info(f"WorkableHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif name == "email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif name == "phone":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"WorkableHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"WorkableHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("WorkableHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"WorkableHandler: set_input_files failed: {e}")
            return False

        resume_base = os.path.splitext(os.path.basename(self.resume_path))[0]
        try:
            self.active_context.wait_for_selector(f"text={resume_base}", timeout=8000)
            logger.info("  -> Upload Verified: True")
        except Exception:
            try:
                self.active_context.wait_for_selector('text=/replace file/i', timeout=4000)
                logger.info("  -> Upload Verified: True (via Replace-file indicator)")
            except Exception:
                logger.info("  -> Upload Verified: False (Could not verify DOM)")
                self._capture_screenshot("resume_verification_failure.png")
                return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("WorkableHandler: Extracting custom questions...")
        questions = []
        label_spans = self.active_context.locator('span[id$="_label"]').all()

        for label_loc in label_spans:
            try:
                if not label_loc.is_visible():
                    continue
                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label or clean_label.lower() in self._STANDARD_LABELS:
                    continue

                container = label_loc.locator("xpath=ancestor::div[1]").first
                if container.count() == 0:
                    continue

                is_required = False
                try:
                    # The "*" marker is a sibling of label_loc's own
                    # immediate parent <span>, not of label_loc itself
                    # (label_loc has no siblings — it's the sole child of
                    # its wrapping span) — go up one level first.
                    prior_marker = label_loc.locator("xpath=../preceding-sibling::span[1]").first
                    is_required = prior_marker.count() > 0 and "*" in prior_marker.inner_text()
                except Exception:
                    pass

                options = []
                widget_type = "unknown"
                placeholder = ""

                radios = container.locator('input[type="radio"]')
                checkboxes = container.locator('input[type="checkbox"]')
                is_select = container.locator('[data-input-type="select"]').count() > 0

                if is_select:
                    widget_type = "workable_select"
                elif radios.count() > 0:
                    widget_type = "radio_group"
                    options = [l.strip() for l in container.locator("label").all_inner_texts() if l.strip()]
                elif checkboxes.count() > 0:
                    widget_type = "checkbox_group"
                elif container.locator("textarea").count() > 0:
                    widget_type = "textarea"
                elif container.locator('input[type="text"], input[type="email"], input[type="tel"], input[type="number"]').count() > 0:
                    widget_type = "input"

                if widget_type == "unknown":
                    continue

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"WorkableHandler: Detected {len(questions)} custom questions.")
        return questions

    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        """Workable's custom "select" widget (e.g. Notice period): the
        real value lives in a hidden input, only reachable by opening the
        widget and clicking the matching visible option."""
        interaction["Selector Used"] = "[data-input-type='select'] -> [role=option]"
        interaction["Interaction Method"] = "click() open, click() option"
        try:
            toggle = container.locator('[data-input-type="select"]').first
            toggle.click(timeout=5000)
            self.page.wait_for_timeout(500)
            option = container.get_by_text(answer, exact=False).first
            if option.count() == 0:
                # Fall back to a page-wide search scoped to the currently
                # open listbox if the option list portals outside the
                # field's own container.
                option = self.page.locator('[role="option"]', has_text=answer).first
            if option.count() == 0:
                return False
            option.click(timeout=3000)
            self.page.wait_for_timeout(300)
            return True
        except Exception as e:
            logger.info(f"WorkableHandler: workable_select interaction failed: {e}")
            return False

    def _custom_field_is_empty(self, container, widget_type: str):
        if widget_type != "workable_select":
            return None
        try:
            visible_text = container.locator('[data-input-type="select"]').first.inner_text()
            return "select an option" in visible_text.lower()
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
