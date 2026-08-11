from src.system.logger import setup_logger
logger = setup_logger('bamboohr')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class BambooHRHandler(BaseATSHandler):
    """
    BambooHR's careers apply form renders directly on the job page once
    "Apply for This Job" is clicked. Standard text fields are plain HTML
    inputs, but Country (and originally State, until a country is picked)
    is a custom "fab-Select" widget: a real `<select>` exists in the DOM
    but is aria-hidden/zero-size, driven instead by a `<button>` toggle
    that opens a searchable option list — same category of problem
    Greenhouse's react-select posed, handled the same way (open, search,
    click the matching option, verify the hidden select's value changed).

    Also present: a `nickname_hpcsaf` honeypot text input (tabindex="-1",
    marked `data-*-ignore="true"` for every password manager) that must
    never be touched, and a visible reCAPTCHA checkbox ("Human Check"
    equivalent) already covered by the shared base_handler pause/resume
    mechanism.
    """
    ATS_NAME = "BAMBOOHR"

    def _enter_application_flow(self):
        logger.info("BambooHRHandler: Entering application flow...")
        try:
            self.page.wait_for_selector('input[name="firstName"]', timeout=3000)
            return
        except Exception:
            pass
        try:
            apply_btn = self.page.get_by_text("Apply for This Job", exact=False).first
            apply_btn.click(timeout=5000)
            self.page.wait_for_selector('input[name="firstName"]', timeout=10000)
        except Exception as e:
            logger.info(f"BambooHRHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _select_fab_option(self, button_locator, search_text: str, timeout: int = 5000) -> bool:
        """Open a fab-Select widget, type into its search box if present,
        and click the option matching search_text exactly."""
        try:
            button_locator.click(timeout=timeout)
            self.page.wait_for_timeout(400)
            search_box = self.page.locator('input[placeholder="Search..."]').first
            if search_box.count() > 0 and search_box.is_visible():
                search_box.fill(search_text)
                self.page.wait_for_timeout(400)
            option = self.page.get_by_text(search_text, exact=True).first
            if option.count() == 0:
                logger.info(f"BambooHRHandler: fab-Select option '{search_text}' not found.")
                return False
            option.click(timeout=timeout)
            self.page.wait_for_timeout(300)
            return True
        except Exception as e:
            logger.info(f"BambooHRHandler: fab-Select interaction failed for '{search_text}': {e}")
            return False

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("BambooHRHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "firstName": self.profile.get_field("first_name"),
            "lastName": self.profile.get_field("last_name"),
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
                    logger.info(f"BambooHRHandler: CRITICAL - Field {name} failed to populate.")
                    safe_to_proceed = False
                elif name == "email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif name == "phone":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"BambooHRHandler: Error filling {name}: {e}")
                safe_to_proceed = False

        # Country must be set BEFORE State/Postal, since choosing a non-US
        # country swaps "State"(dropdown) -> "Province"(text) and
        # "ZIP" -> "Postal Code" in the live DOM.
        country = self.profile.get_field("country") or "India"
        country_btn = self.page.locator('button[aria-label*="Country" i]').first
        if country_btn.count() > 0:
            if not self._select_fab_option(country_btn, country):
                logger.info("BambooHRHandler: CRITICAL - Could not set Country.")
                safe_to_proceed = False

        text_fields = {
            "streetAddress.value": self.profile.get_field("address"),
            "city.value": self.profile.get_field("city"),
            "state.value": self.profile.get_field("state"),
            "zip.value": self.profile.get_field("postal_code"),
        }
        for name, val in text_fields.items():
            if not val:
                continue
            el = self.active_context.locator(f'input[name="{name}"]').first
            if el.count() == 0:
                continue
            try:
                self._human_type(el, val)
            except Exception as e:
                logger.info(f"BambooHRHandler: Error filling {name} (non-fatal): {e}")

        # Date Available* — a plain text input with an mm/dd/yyyy
        # placeholder rather than a real type="date" widget.
        date_el = self.active_context.locator('input[placeholder="mm/dd/yyyy"]').first
        if date_el.count() > 0:
            answer = self._ask("Date you are available to start this job", field_type="date", label_text="Date Available mm/dd/yyyy", required=True)
            if answer:
                try:
                    self._human_type(date_el, answer)
                except Exception as e:
                    logger.info(f"BambooHRHandler: Error filling Date Available: {e}")
                    safe_to_proceed = False
            else:
                safe_to_proceed = False

        desired_pay_el = self.active_context.locator('input[name="desiredPay"]').first
        if desired_pay_el.count() > 0:
            answer = self._ask("Expected pay / desired salary compensation", field_type="text", label_text="Desired Pay", required=True)
            if answer:
                try:
                    self._human_type(desired_pay_el, answer)
                except Exception as e:
                    logger.info(f"BambooHRHandler: Error filling Desired Pay: {e}")
            else:
                safe_to_proceed = False

        linkedin_el = self.active_context.locator('input[name="linkedinUrl"]').first
        if linkedin_el.count() > 0:
            linkedin = self.profile.get_field("linkedin")
            if linkedin:
                try:
                    self._human_type(linkedin_el, linkedin)
                except Exception as e:
                    logger.info(f"BambooHRHandler: Error filling LinkedIn URL: {e}")
            else:
                safe_to_proceed = False

        # Optional: Website/Blog/Portfolio.
        portfolio_el = self.active_context.locator('input[name="websiteUrl"]').first
        portfolio = self.profile.get_field("portfolio") or self.profile.get_field("github")
        if portfolio_el.count() > 0 and portfolio:
            try:
                self._human_type(portfolio_el, portfolio)
            except Exception as e:
                logger.info(f"BambooHRHandler: Error filling website/portfolio (non-fatal): {e}")

        # NEVER touch the honeypot (#nickname_hpcsaf) — leaving it blank is
        # the correct, intentional behavior, not an oversight.

        return safe_to_proceed

    def _ask(self, question: str, field_type: str = "text", label_text: str = "", required: bool = True) -> str:
        dom_meta = {"css_selector": "", "input_tag": field_type, "visible": True, "disabled": False, "current_value": "", "widget_type": field_type}
        answer = self.engine.answer(question=question, field_type=field_type, label_text=label_text, required=required, dom_meta=dom_meta)
        if answer in ("NORMALIZATION_FAILED", "REVIEW_REQUIRED"):
            return ""
        return answer

    def _upload_resume(self) -> bool:
        logger.info(f"BambooHRHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        # Two file inputs exist (Cover Letter, then Resume) sharing no
        # distinguishing name/id — the hidden `resumeFileId`/
        # `coverLetterFileId` companions confirm which is which via DOM
        # order, matching the resumeFileId locator used for verification.
        file_inputs = self.active_context.locator('input[type="file"]')
        if file_inputs.count() < 2:
            logger.info("BambooHRHandler: Expected 2 file inputs (cover letter, resume), found fewer.")
            if file_inputs.count() == 0:
                return False

        resume_input = file_inputs.nth(file_inputs.count() - 1)
        try:
            resume_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"BambooHRHandler: set_input_files failed: {e}")
            return False

        # The file itself uploads to BambooHR's backend asynchronously;
        # resumeFileId only populates once that request completes, which
        # can take longer than a fixed short wait under real network
        # conditions — poll briefly instead of a single fixed sleep.
        resume_file_id = ""
        for _ in range(10):
            self.page.wait_for_timeout(500)
            try:
                resume_file_id = self.active_context.locator('input[name="resumeFileId"]').first.input_value()
            except Exception:
                resume_file_id = ""
            if resume_file_id:
                break

        if not resume_file_id:
            logger.info("  -> Upload Verified: False (resumeFileId empty)")
            self._capture_screenshot("resume_verification_failure.png")
            return False

        logger.info("  -> Upload Verified: True (resumeFileId populated)")
        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("BambooHRHandler: Extracting custom questions...")
        questions = []
        containers = self.active_context.locator('input[name^="customQuestionAnswers."], textarea[name^="customQuestionAnswers."]').all()

        for input_el in containers:
            try:
                if not input_el.is_visible():
                    continue
                # The visible question text sits as a preceding sibling
                # paragraph in the same field block, not a <label> tied to
                # this input via for/id.
                block = input_el.locator("xpath=ancestor::div[3]").first
                raw_text = ""
                try:
                    full_text = block.inner_text()
                    raw_text = full_text.split("\n")[0].strip()
                except Exception:
                    pass
                if not raw_text:
                    continue
                clean_label = raw_text.replace("*", "").strip()
                is_required = "*" in raw_text
                tag = input_el.evaluate("e => e.tagName").lower()
                widget_type = "textarea" if tag == "textarea" else "input"

                questions.append({
                    "container": input_el, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": [], "placeholder": "",
                })
            except Exception:
                pass

        logger.info(f"BambooHRHandler: Detected {len(questions)} custom questions.")
        return questions

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        # Custom questions here pass the raw <input>/<textarea> itself as
        # "container" (no separate wrapper to search descendants of), so
        # fill it directly rather than going through the base class's
        # container.locator(...) lookup.
        try:
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
        # Same "container IS the input, not a wrapper" situation as
        # _interact_widget above — the base class's generic empty-check
        # searches container.locator(...) for descendants, which is always
        # empty for a leaf input/textarea, silently passing the pre-submit
        # audit on an actually-blank required field. Check the element's
        # own value directly instead.
        if widget_type not in ("input", "textarea"):
            return None
        try:
            return not container.input_value().strip()
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.get_by_role("button", name=re.compile("submit application", re.I)).first
