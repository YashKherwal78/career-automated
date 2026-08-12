from src.system.logger import setup_logger
logger = setup_logger('ashby')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class AshbyHandler(BaseATSHandler):
    """
    Ashby renders directly in the main page (no iframe hop needed, unlike
    Greenhouse) with a stable container class
    (.ashby-application-form-field-entry) regardless of the per-tenant
    hashed CSS classes around it. Most widgets are native
    radio/checkbox/select, but boolean questions render as a styled
    Yes/No button pair backed by a hidden checkbox rather than a real
    radio group, which is the one thing this handler needs its own
    interaction logic for.
    """
    ATS_NAME = "ASHBY"

    def _enter_application_flow(self):
        logger.info("AshbyHandler: Entering application flow...")
        try:
            apply_btn = self.page.get_by_text("Apply for this Job", exact=False).first
            apply_btn.click(timeout=5000)
            self.page.wait_for_timeout(1500)
        except Exception as e:
            logger.info(f"AshbyHandler: Apply click skipped/failed (may already be on the form): {e}")

    def _detect_and_set_iframe(self):
        # Ashby's form lives directly in the main page DOM.
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("AshbyHandler: Verifying standard fields...")
        safe_to_proceed = True

        full_name = f"{self.profile.get_field('first_name') or ''} {self.profile.get_field('last_name') or ''}".strip()
        text_fields = {
            "#_systemfield_name": full_name,
            "#_systemfield_email": self.profile.get_field("email"),
        }
        for selector, val in text_fields.items():
            if not val:
                continue
            el = self.active_context.locator(selector).first
            if el.count() == 0:
                continue
            try:
                self._human_type(el, val)
                self.page.wait_for_timeout(150)
                if not el.input_value():
                    logger.info(f"AshbyHandler: CRITICAL - Field {selector} failed to populate.")
                    safe_to_proceed = False
                elif "email" in selector:
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
            except Exception as e:
                logger.info(f"AshbyHandler: Error filling {selector}: {e}")
                safe_to_proceed = False

        # Phone has no stable system-field id on this ATS (it's rendered as
        # a per-tenant custom question) — target it by input type instead.
        phone = self.profile.get_field("phone")
        phone_el = self.active_context.locator('input[type="tel"]').first
        if phone and phone_el.count() > 0:
            try:
                self._human_type(phone_el, phone)
                if phone_el.input_value():
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"AshbyHandler: Error filling phone: {e}")

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"AshbyHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        # The real file input is visually hidden (clip-path trick) behind a
        # styled "Upload file" button, but it's still a genuine <input
        # type=file> — set_input_files works on it directly without needing
        # to intercept a file-chooser dialog.
        # Ashby's application form is a React SPA — the file input can mount
        # after the rest of the form is visible (same race Greenhouse hit
        # and was fixed for in commit 71bc99d: absent at 1.5s, present by
        # 4s there). This had no wait at all, so a slow mount meant
        # count() == 0 and an immediate, unretried give-up.
        try:
            self.active_context.wait_for_selector('#_systemfield_resume, input[type="file"]', timeout=8000)
        except Exception:
            pass

        file_input = self.active_context.locator('#_systemfield_resume, input[type="file"]').first
        if file_input.count() == 0:
            logger.info("AshbyHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"AshbyHandler: set_input_files failed: {e}")
            return False

        resume_base = os.path.splitext(os.path.basename(self.resume_path))[0]
        try:
            self.active_context.wait_for_selector(f"text={resume_base}", timeout=8000)
            logger.info("  -> Upload Verified: True")
        except Exception:
            try:
                self.active_context.wait_for_selector('text=/remove|change file/i', timeout=4000)
                logger.info("  -> Upload Verified: True (via Remove/Change indicator)")
            except Exception:
                logger.info("  -> Upload Verified: False (Could not verify DOM)")
                self._capture_screenshot("resume_verification_failure.png")
                return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("AshbyHandler: Extracting questions...")
        questions = []
        # Radio-group questions ("Where are you located?" etc.) render as a
        # bare <fieldset> with only hashed CSS-module classes, not the
        # stable `.ashby-application-form-field-entry` class every other
        # widget type uses — leaving them completely invisible to the
        # extractor and silently unfilled. Include `fieldset` too, but skip
        # any container that has ANOTHER matching container nested inside
        # it (keep only the innermost) so a wrapper fieldset around an
        # already-matched field-entry div doesn't get extracted twice.
        raw_containers = self.active_context.locator(".ashby-application-form-field-entry, fieldset").all()
        containers = [
            c for c in raw_containers
            if c.locator(".ashby-application-form-field-entry, fieldset").count() == 0
        ]

        # "Name" is the same system field _fill_and_verify_standard_fields()
        # already fills via #_systemfield_name — but its visible label text
        # varies per tenant ("Name" vs "Full Name"), and only the latter was
        # excluded here, so the former got re-extracted as an unanswered
        # custom question and escalated every time despite already being
        # correctly filled.
        skip_list = ["name", "full name", "email", "phone", "resume"]

        for container in containers:
            try:
                if not container.is_visible():
                    continue
                # Consent-checkbox fields (data-processing agreements etc.)
                # render the standard ".ashby-application-form-question-title"
                # label EMPTY — the real prompt text lives in a second,
                # separate <label> that wraps the checkbox input itself. Found
                # via a real submission where this silently dropped a
                # required consent checkbox entirely: `.first` picked the
                # empty title label, produced an empty clean_label, and the
                # field never even reached the is_required check below.
                label_loc = container.locator(".ashby-application-form-question-title, label").first
                if label_loc.count() == 0:
                    continue
                raw_text = label_loc.inner_text().split("\n")[0].strip()
                if not raw_text:
                    for lbl in container.locator("label").all():
                        try:
                            t = lbl.inner_text().strip()
                        except Exception:
                            continue
                        if t:
                            raw_text = t.split("\n")[0].strip()
                            break
                clean_label = raw_text.strip()
                if not clean_label or clean_label.lower() in skip_list:
                    continue
                if container.locator('input[type="file"]').count() > 0:
                    continue  # resume, handled separately

                # Ashby marks required fields two different ways: a real
                # `required`/`aria-required` attribute on most fields, but a
                # `_required_...` (hashed) CSS class on the title label for
                # at least the consent-checkbox pattern above — checked via
                # a stable prefix match, not the exact hash suffix.
                is_required = (
                    container.locator('[required], [aria-required="true"]').count() > 0
                    or "required" in (container.get_attribute("class") or "").lower()
                    or bool(re.search(r"\brequired", label_loc.get_attribute("class") or "", re.IGNORECASE))
                )

                options = []
                widget_type = "unknown"
                placeholder = ""

                yesno_buttons = container.locator("button")
                yesno_texts = [b.inner_text().strip() for b in yesno_buttons.all()] if yesno_buttons.count() > 0 else []
                is_yesno = set(t.lower() for t in yesno_texts) == {"yes", "no"}

                radios = container.locator('input[type="radio"]')
                checkboxes = container.locator('input[type="checkbox"]')

                if is_yesno:
                    widget_type = "yesno_buttons"
                    options = ["Yes", "No"]
                elif container.locator("select").count() > 0:
                    widget_type = "native_select"
                    options = [o.strip() for o in container.locator("option").all_inner_texts() if o.strip() and "select" not in o.lower()]
                elif radios.count() > 0 or checkboxes.count() > 0:
                    widget_type = "radio_group" if radios.count() > 0 else "checkbox_group"
                    labels = container.locator("label").all_inner_texts()
                    options = [l.strip() for l in labels if l.strip() and l.strip() != clean_label]
                elif container.locator("textarea").count() > 0:
                    widget_type = "textarea"
                    ph = container.locator("textarea").first.get_attribute("placeholder")
                    if ph: placeholder = ph
                elif container.locator('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"])').count() > 0:
                    # Broad text-like match, not an explicit type allowlist:
                    # Ashby renders both plain `type="number"` inputs (e.g.
                    # Notice Period) and combobox-style autocomplete inputs
                    # with NO type attribute at all (e.g. the Location
                    # field) — an allowlist of text/email/tel/url misses
                    # both, leaving them as "unknown", which then falls
                    # through to this handler's yes/no-button interaction
                    # (wrong for any non-yes/no field) instead of the normal
                    # text-input fill path.
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

        logger.info(f"AshbyHandler: Detected {len(questions)} questions.")
        return questions

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first

    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        """Handles Ashby's Yes/No button-pair widget (a styled button pair
        backed by a hidden checkbox, not a real radio group)."""
        interaction["Selector Used"] = "button (yes/no)"
        interaction["Interaction Method"] = "click()"
        target = "yes" if answer.strip().lower() in ["yes", "true"] else "no"
        buttons = container.locator("button").all()
        for b in buttons:
            if b.inner_text().strip().lower() == target:
                b.click(timeout=3000, force=True)
                return True
        return False

    def _custom_field_is_empty(self, container, widget_type: str):
        if widget_type != "yesno_buttons":
            return None
        chk = container.locator('input[type="checkbox"]').first
        if chk.count() == 0:
            return True
        try:
            return not chk.is_checked()
        except Exception:
            return True
