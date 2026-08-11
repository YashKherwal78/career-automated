from src.system.logger import setup_logger
logger = setup_logger('recruitee')
import os
import random
import re
from src.applications.handlers.base_handler import BaseATSHandler

class RecruiteeHandler(BaseATSHandler):
    """
    Recruitee postings render the job description and application form on
    the same page, switched via an "Application" tab (the form's inputs
    exist in the DOM immediately but stay hidden/inactive until that tab
    is selected). Standard fields use clean, stable `candidate.*` names.

    The phone field's country selector is a virtualized list (only the
    options near the current scroll position exist in the DOM at any
    moment, so a plain text search for e.g. "India" fails until it's
    scrolled into view) — but the widget supports native type-ahead: with
    the dropdown open, typing a country name jumps/highlights it into
    view without needing a dedicated search box.
    """
    ATS_NAME = "RECRUITEE"

    def _enter_application_flow(self):
        logger.info("RecruiteeHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('input[name="candidate.name"]', timeout=2000)
            if self.page.locator('input[name="candidate.name"]').first.is_visible():
                return
        except Exception:
            pass
        try:
            # Tenant boards render in the employer's own locale (Dutch
            # "Solliciteren", etc.), so matching the tab by English text
            # misses most non-English postings entirely, leaving the
            # whole form hidden/invisible for the rest of the run. Every
            # posting has exactly two tabs in a fixed order — job details
            # first, application second — regardless of language.
            tab = self.page.get_by_role("tab", name="Apply", exact=False).first
            if tab.count() == 0:
                tab = self.page.get_by_role("tab", name="Application", exact=False).first
            if tab.count() == 0:
                tabs = self.page.get_by_role("tab")
                if tabs.count() >= 2:
                    tab = tabs.nth(1)
            tab.click(timeout=5000)
            self.page.wait_for_selector('input[name="candidate.name"]', timeout=10000)
        except Exception as e:
            logger.info(f"RecruiteeHandler: Application-tab click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("RecruiteeHandler: Verifying standard fields...")
        safe_to_proceed = True

        full_name = f"{self.profile.get_field('first_name') or ''} {self.profile.get_field('last_name') or ''}".strip()
        fields = {
            "candidate.name": full_name,
            "candidate.email": self.profile.get_field("email"),
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
                    logger.info(f"RecruiteeHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif name == "candidate.email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
            except Exception as e:
                logger.info(f"RecruiteeHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        # Phone country selector defaults to whatever the tenant's board
        # is configured for (often the employer's own country, not the
        # candidate's) — must be set before the number itself, since
        # picking a country resets whatever's already in the number field.
        phone_el = self.active_context.locator('input[name="candidate.phone"]').first
        if phone_el.count() > 0:
            country = self.profile.get_field("country") or "India"
            try:
                # The country-select button isn't a direct sibling of the
                # phone <input> — it's nested inside the immediately
                # preceding sibling <div> (id pattern
                # "country-select-input-candidate.phone-<n>").
                country_btn = phone_el.locator("xpath=preceding-sibling::div[1]//button").first
                if country_btn.count() == 0:
                    country_btn = self.active_context.locator('button[aria-haspopup="listbox"]').first
                if country_btn.count() > 0 and country not in (country_btn.inner_text() or ""):
                    country_btn.click(timeout=5000)
                    self.page.wait_for_timeout(400)
                    # This widget's type-ahead search resets per keystroke
                    # rather than accumulating a buffer if characters
                    # arrive too fast — Playwright's default typing speed
                    # landed on the wrong country because the search
                    # restarted mid-word.
                    self.page.keyboard.type(country, delay=150)
                    self.page.wait_for_timeout(500)
                    # Scoped to role=option specifically — a bare text
                    # search also matches the flag <svg><title>India</title>
                    # accessibility label on every OTHER visible country's
                    # flag icon, none of which are ever clickable/visible.
                    # Substring, not an exact ^$ anchor: the option's
                    # inner_text() includes the flag's own accessible name
                    # alongside the visible label, so an exact match never
                    # succeeds even against the right element. Alphabetical
                    # DOM order means .first still lands on "India" over
                    # "Indonesia" for this candidate.
                    option = self.page.locator('[role="option"]', has_text=country).first
                    if option.count() > 0:
                        option.click(timeout=3000)
                        self.page.wait_for_timeout(300)
            except Exception as e:
                logger.info(f"RecruiteeHandler: Phone country selection failed (non-fatal): {e}")

            phone = self.profile.get_field("phone")
            if phone:
                try:
                    # Deliberately NOT the shared _human_type() helper: it
                    # clears the field first via .fill(""), and that clear
                    # call alone is enough to put this widget's live
                    # country-auto-detect into a state where it then
                    # mis-reads the candidate's number (starts with "98" —
                    # Iran's calling code) and silently swaps the country
                    # away from the one just explicitly selected above.
                    # A fresh field + real keystrokes with no prior
                    # clear-fill does not trigger that misdetection
                    # (confirmed repeatedly against the live widget).
                    phone_el.click(timeout=3000)
                    phone_el.type(phone, delay=random.randint(60, 120))
                    self.page.wait_for_timeout(200)
                    if phone_el.input_value():
                        self.telemetry.setdefault("filled_fields", {})["Phone"] = True
                except Exception as e:
                    logger.info(f"RecruiteeHandler: Error filling phone: {e}")

            if country not in (country_btn.inner_text() or ""):
                logger.info(f"RecruiteeHandler: CRITICAL - Country selection shows {country_btn.inner_text()!r} after phone entry, expected {country!r}.")
                safe_to_proceed = False

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"RecruiteeHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('input[name="candidate.cv"]').first
        if file_input.count() == 0:
            file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("RecruiteeHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"RecruiteeHandler: set_input_files failed: {e}")
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
        logger.info("RecruiteeHandler: Extracting custom questions...")
        questions = []
        handled_names = {"candidate.name", "candidate.email", "candidate.phone", "candidate.textingConsent",
                          "candidate.photo", "candidate.cv", "candidate.coverLetterFile"}

        labels = self.active_context.locator("label").all()
        for label_loc in labels:
            try:
                if not label_loc.is_visible():
                    continue
                for_id = label_loc.get_attribute("for")
                target = None
                if for_id:
                    target = self.active_context.locator(f'#{for_id}').first
                else:
                    inner = label_loc.locator('input, textarea, select').first
                    if inner.count() > 0:
                        target = inner
                if target is None or target.count() == 0:
                    continue
                name = target.get_attribute("name") or ""
                if name in handled_names:
                    continue
                if target.get_attribute("type") == "file":
                    continue

                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue
                is_required = "*" in raw_text

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
                elif typ not in ("hidden", "file"):
                    widget_type = "input"

                if widget_type == "unknown":
                    continue

                container = for_id and self.active_context.locator(
                    f'xpath=//label[@for="{for_id}"]/ancestor::*[.//*[@id="{for_id}"]][1]'
                ).first or label_loc

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"RecruiteeHandler: Detected {len(questions)} custom questions.")
        return questions

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("^send$", re.I)).first
