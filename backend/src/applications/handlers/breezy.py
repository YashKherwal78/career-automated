from src.system.logger import setup_logger
logger = setup_logger('breezy')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class BreezyHandler(BaseATSHandler):
    """
    Breezy HR renders a plain AngularJS-driven HTML form directly on the
    main page (no iframe, no captcha observed on any tenant scouted so
    far) at `<job_url>/apply`. Unlike Lever/Ashby, "Work History" and
    "Education" aren't flat lists of individually-labelled questions —
    each is a repeatable `<li class="experience">` compound record
    (Company/Title/Summary/dates, or School/Field of Study/Summary/dates)
    added via an "Add Position"/"Add Education" button, and both entry
    types share the exact same `experience` class — only their
    `ng-repeat` attribute ("...work_history" vs "...education")
    disambiguates them. Because these sub-fields have no unique wrapper
    per field (all of one entry's inputs sit as siblings inside one
    `<li>`), they can't go through the shared per-question container
    pipeline (_process_custom_fields) and are filled directly here via
    the same QuestionEngine used everywhere else.

    Also present: a spam-trap honeypot text input (`name="hp_7f2b"`) that
    must be left completely untouched — filling it is what a scripted
    bot would do and is very likely used server-side to silently reject
    the submission.
    """
    ATS_NAME = "BREEZY"

    _HONEYPOT_NAME_PATTERN = re.compile(r"^hp_")

    def _enter_application_flow(self):
        logger.info("BreezyHandler: Entering application flow...")
        if "/apply" not in self.page.url:
            # Tenants label this link differently ("Apply To Position",
            # "Apply Now", etc.) but it always resolves to a URL ending in
            # "/apply" — match on that instead of exact wording.
            try:
                apply_link = self.page.locator('a[href$="/apply"]').first
                if apply_link.count() > 0:
                    apply_link.click(timeout=5000)
                else:
                    apply_link = self.page.get_by_role("link", name=re.compile(r"apply (to position|now)", re.I)).first
                    apply_link.click(timeout=5000)
            except Exception as e:
                logger.info(f"BreezyHandler: Apply-link click failed (may already be on apply page): {e}")
        try:
            self.page.wait_for_selector('input[name="cName"]', timeout=10000)
        except Exception as e:
            logger.info(f"BreezyHandler: Apply form did not appear: {e}")

    def _detect_and_set_iframe(self):
        # Breezy's form renders directly in the main page — no iframe hop needed.
        self.active_context = self.page

    def _ask(self, question: str, field_type: str = "text", label_text: str = "", required: bool = True) -> str:
        """Route one synthetic sub-field question through the same
        QuestionEngine every other handler uses, instead of hardcoding
        candidate facts here."""
        dom_meta = {"css_selector": "", "input_tag": field_type, "visible": True, "disabled": False, "current_value": "", "widget_type": field_type}
        answer = self.engine.answer(question=question, field_type=field_type, label_text=label_text, required=required, dom_meta=dom_meta)
        if answer in ("NORMALIZATION_FAILED", "REVIEW_REQUIRED"):
            return ""
        return answer

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("BreezyHandler: Verifying standard fields...")
        safe_to_proceed = True

        full_name = f"{self.profile.get_field('first_name') or ''} {self.profile.get_field('last_name') or ''}".strip()
        fields = {
            "cName": full_name,
            "cEmail": self.profile.get_field("email"),
            "cPhoneNumber": self.profile.get_field("phone"),
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
                    logger.info(f"BreezyHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif name == "cEmail":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif name == "cPhoneNumber":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"BreezyHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        address = self.profile.get_field("current_location") or self.profile.get_field("address")
        addr_el = self.active_context.locator('input[name="cAddress"]').first
        if address and addr_el.count() > 0:
            try:
                self._human_type(addr_el, address)
            except Exception as e:
                logger.info(f"BreezyHandler: Error filling address (non-fatal): {e}")

        # Desired Salary + pay-period select.
        salary_el = self.active_context.locator('input[name="cSalary"]').first
        if salary_el.count() > 0:
            salary = self._ask("Desired salary / expected compensation", field_type="text", label_text="Desired Salary", required=True)
            if salary:
                try:
                    self._human_type(salary_el, salary)
                except Exception as e:
                    logger.info(f"BreezyHandler: Error filling desired salary: {e}")
            period_select = self.active_context.locator("select").first
            if period_select.count() > 0:
                try:
                    period_select.select_option(label="Yearly")
                    period_select.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
                except Exception as e:
                    logger.info(f"BreezyHandler: Error setting pay period (non-fatal): {e}")

        # Experience Summary is deliberately NOT filled here — it's filled
        # at the end of _upload_resume() instead, since Breezy's async
        # resume-parse (triggered by the upload that happens after this
        # method returns) rebinds `candidate.summary` from the parsed
        # resume and was silently clobbering whatever was typed here back
        # to empty. Filling it after that settles is the only way it
        # actually sticks.

        # Required privacy/GDPR consent — same fixed "Yes" treatment every
        # other handler gives an explicit data-processing consent checkbox.
        gdpr_el = self.active_context.locator('input[name="gdprAgreement"]').first
        if gdpr_el.count() > 0:
            if not self._click_and_verify_checked(gdpr_el):
                logger.info("BreezyHandler: CRITICAL - Could not check required GDPR consent.")
                safe_to_proceed = False

        # NEVER touch the honeypot (input[name^="hp_"]) — leaving it blank
        # is the correct, intentional behavior, not an oversight.

        return safe_to_proceed

    def _work_history_auto_populated(self) -> bool:
        """Breezy parses the uploaded resume and auto-appends Work
        History/Education entries a few seconds after upload — often more
        complete than a single synthetic entry. Only add one manually if
        that didn't happen (e.g. a resume format it couldn't parse)."""
        entries = self.active_context.locator('li[ng-repeat*="work_history"] input[placeholder="Company"]')
        for i in range(entries.count()):
            try:
                if entries.nth(i).input_value().strip():
                    return True
            except Exception:
                pass
        return False

    def _education_auto_populated(self) -> bool:
        entries = self.active_context.locator('li[ng-repeat*="education"] input[placeholder="School"]')
        for i in range(entries.count()):
            try:
                if entries.nth(i).input_value().strip():
                    return True
            except Exception:
                pass
        return False

    def _fill_work_history(self) -> bool:
        if self._work_history_auto_populated():
            logger.info("BreezyHandler: Work History already auto-populated from resume parse — skipping manual entry.")
            return True

        add_btn = self.page.get_by_text("Add Position", exact=False).first
        if add_btn.count() == 0:
            return True
        try:
            add_btn.click(timeout=5000)
            self.page.wait_for_timeout(500)
        except Exception as e:
            logger.info(f"BreezyHandler: Add Position click failed: {e}")
            return True  # not required to add an entry if the button isn't there

        entry = self.active_context.locator('li[ng-repeat*="work_history"]').last
        if entry.count() == 0:
            return True

        ok = True
        company = self._ask("Employer / company name for your most recent position", field_type="text", label_text="Company")
        title = self._ask("Job title held at your most recent position", field_type="text", label_text="Title")
        summary = self._ask("Brief description of your responsibilities in that position", field_type="textarea", label_text="Summary")
        start = self._ask("Employment start date for that position", field_type="date", label_text="Start date")
        end = self._ask("Employment end date for that position", field_type="date", label_text="End date")

        try:
            if company:
                self._human_type(entry.locator('input[placeholder="Company"]').first, company)
            if title:
                self._human_type(entry.locator('input[placeholder="Title"]').first, title)
            if summary:
                self._human_type(entry.locator('textarea[placeholder="Summary"]').first, summary)
            dates = entry.locator('input[type="date"]')
            if start and dates.count() > 0:
                dates.nth(0).fill(start)
            if end and dates.count() > 1:
                dates.nth(1).fill(end)
        except Exception as e:
            logger.info(f"BreezyHandler: Error filling work history entry: {e}")
            ok = False

        return ok

    def _fill_education(self) -> bool:
        if self._education_auto_populated():
            logger.info("BreezyHandler: Education already auto-populated from resume parse — skipping manual entry.")
            return True

        add_btn = self.page.get_by_text("Add Education", exact=False).first
        if add_btn.count() == 0:
            return True
        try:
            add_btn.click(timeout=5000)
            self.page.wait_for_timeout(500)
        except Exception as e:
            logger.info(f"BreezyHandler: Add Education click failed: {e}")
            return True

        entry = self.active_context.locator('li[ng-repeat*="education"]').last
        if entry.count() == 0:
            return True

        ok = True
        school = self._ask("Name of the school / university / institute you attended", field_type="text", label_text="School")
        field_of_study = self._ask("Your degree and field of study", field_type="text", label_text="Field of Study")
        start = self._ask("Education start date", field_type="date", label_text="Start date")
        end = self._ask("Education end date", field_type="date", label_text="End date")

        try:
            if school:
                self._human_type(entry.locator('input[placeholder="School"]').first, school)
            if field_of_study:
                self._human_type(entry.locator('input[placeholder="Field of Study"]').first, field_of_study)
            dates = entry.locator('input[type="date"]')
            if start and dates.count() > 0:
                dates.nth(0).fill(start)
            if end and dates.count() > 1:
                dates.nth(1).fill(end)
        except Exception as e:
            logger.info(f"BreezyHandler: Error filling education entry: {e}")
            ok = False

        return ok

    def _upload_resume(self) -> bool:
        logger.info(f"BreezyHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('#main-attachment, input[name="cResume"], input[type="file"]').first
        if file_input.count() == 0:
            logger.info("BreezyHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"BreezyHandler: set_input_files failed: {e}")
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

        # Breezy asynchronously parses the uploaded resume and appends
        # Work History/Education <li> entries a few seconds later — give
        # that a moment to finish before deciding whether a manual
        # fallback entry is needed.
        self.page.wait_for_timeout(3000)
        work_ok = self._fill_work_history()
        edu_ok = self._fill_education()
        summary_ok = self._fill_experience_summary()
        return work_ok and edu_ok and summary_ok

    def _fill_experience_summary(self) -> bool:
        # Phrased/labelled carefully to dodge two ResponseNormalizer traps:
        # "background" collides with the LEGAL classifier's background-CHECK
        # keyword, and a label_text containing "experience" sends any answer
        # with no digits in it through the numeric years-of-experience
        # extractor, which finds nothing and returns NORMALIZATION_FAILED.
        exp_summary_el = self.active_context.locator('textarea[name="cSummary"]').first
        if exp_summary_el.count() == 0:
            return True
        summary = self._ask("Give a short professional summary describing your skills", field_type="textarea", label_text="Professional Summary", required=True)
        if not summary:
            logger.info("BreezyHandler: CRITICAL - Experience Summary (required) unanswerable.")
            return False
        try:
            self._human_type(exp_summary_el, summary)
            if exp_summary_el.input_value().strip() != summary.strip():
                logger.info("BreezyHandler: CRITICAL - Experience Summary did not stick after fill.")
                return False
        except Exception as e:
            logger.info(f"BreezyHandler: Error filling experience summary: {e}")
            return False
        return True

    def _extract_questions(self) -> list[dict]:
        # Work history, education, salary, experience summary and the GDPR
        # consent are all handled directly in _fill_and_verify_standard_fields
        # above (they're compound multi-field records, not flat labelled
        # questions a generic container-based extractor can address safely).
        # Some tenants may add genuinely custom per-job questions below the
        # standard section; scan for them defensively, skipping every field
        # already handled above plus the honeypot.
        logger.info("BreezyHandler: Extracting custom questions...")
        questions = []
        handled_names = {"cName", "cEmail", "cPhoneNumber", "cAddress", "cSalary", "cResume", "smsConsent", "gdprAgreement"}

        containers = self.active_context.locator("label").all()
        for label_loc in containers:
            try:
                if not label_loc.is_visible():
                    continue
                for_id = label_loc.get_attribute("for")
                target = None
                if for_id:
                    target = self.active_context.locator(f'#{for_id}').first
                else:
                    inner_input = label_loc.locator('input, textarea, select').first
                    if inner_input.count() > 0:
                        target = inner_input
                if target is None or target.count() == 0:
                    continue
                name = target.get_attribute("name") or ""
                if name in handled_names or self._HONEYPOT_NAME_PATTERN.match(name):
                    continue
                # Skip anything already inside a work-history/education
                # entry or the file input — those are handled above.
                if target.evaluate("e => !!e.closest('li.experience')") or (target.get_attribute("type") == "file"):
                    continue

                raw_text = label_loc.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue

                tag = target.evaluate("e => e.tagName").lower()
                typ = (target.get_attribute("type") or "").lower()
                is_required = target.get_attribute("required") is not None or "*" in raw_text

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
                elif typ not in ("hidden", "file"):
                    widget_type = "input"

                # Build a container that actually wraps the widget (the
                # <label> itself, since for_id-based targets live as
                # siblings, not descendants, of their <label>) so the
                # shared _interact_widget's container.locator(...) calls
                # resolve correctly.
                if for_id:
                    container = self.active_context.locator(
                        f'xpath=//label[@for="{for_id}"]/ancestor::*[.//*[@id="{for_id}"]][1]'
                    ).first
                else:
                    container = label_loc

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"BreezyHandler: Detected {len(questions)} custom questions.")
        return questions

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
