"""
Shared auto-apply orchestration, factored out of the original Greenhouse-only
handler once Ashby and Lever needed the same engine. Mirrors the discovery
crawler's connector-plugin split: this base owns the state machine (fill ->
upload -> answer questions -> pre-submit audit -> OTP -> submit -> verify ->
retry), and each ATS subclass only implements the DOM-specific primitives
(how to find the standard fields, how to extract question containers, how to
upload a resume, where the submit button is). Widget interaction (input,
textarea, native <select>, radio/checkbox groups) is standard HTML and is
handled here; a subclass only needs to override `_interact_custom_dropdown`
if that ATS uses a non-native dropdown widget (Greenhouse's React Select
does; Lever and Ashby's native <select>/<input> based forms don't).
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
import os
import random

from playwright.sync_api import Page
from src.system.logger import setup_logger
from src.system.state import WorkflowState
from src.applications.question_engine import QuestionEngine, translate_to_english
from src.applications.question_classifier import QuestionClassifier
from src.applications.otp_retriever import retrieve_greenhouse_otp as retrieve_application_otp
from src.applications.verifier import SubmissionVerifier

logger = setup_logger("ats_handler")


class BaseATSHandler(ABC):
    ATS_NAME: str = "UNKNOWN"

    def __init__(self, page: Page, job_title: str, company_name: str, location: str, resume_path: str,
                 test_mode: bool = False, execution_dir: str = "", profile_manager=None, rag_client=None,
                 llm_client=None, company_context: str = ""):
        self.page = page
        self.job_title = job_title
        self.company_name = company_name
        self.location = location
        self.resume_path = resume_path
        self.test_mode = test_mode
        self.execution_dir = execution_dir
        self.profile = profile_manager
        self.engine = QuestionEngine(
            profile_manager=profile_manager,
            rag_client=rag_client,
            llm_client=llm_client,
            company_context=company_context,
            job_title=job_title,
            job_location=location,
        )
        self.active_context = self.page

    # ------------------------------------------------------------------
    # ATS-specific primitives — every subclass must implement these.
    # ------------------------------------------------------------------

    @abstractmethod
    def _enter_application_flow(self):
        """Navigate from the job posting to the actual application form
        (e.g. click an "Apply" button) and leave self.page on that form."""
        ...

    @abstractmethod
    def _detect_and_set_iframe(self):
        """Set self.active_context to whichever frame the form actually
        lives in (or leave it as self.page if there's no iframe)."""
        ...

    @abstractmethod
    def _fill_and_verify_standard_fields(self) -> bool:
        """Fill name/email/phone (and any other ATS-standard fields) and
        return False if a critical one failed to populate."""
        ...

    @abstractmethod
    def _upload_resume(self) -> bool:
        ...

    @abstractmethod
    def _extract_questions(self) -> list[dict]:
        """Return a list of dicts, each shaped like:
        {container, question, raw_label, is_required, widget_type, options, placeholder}
        widget_type must be one of: input, textarea, native_select,
        radio_group, checkbox_group, or an ATS-specific custom type that
        _interact_custom_dropdown / _pre_submit_audit_custom know how to
        handle (e.g. Greenhouse's "react_select")."""
        ...

    @abstractmethod
    def _get_submit_button_locator(self):
        ...

    # Optional override: only needed if this ATS has a non-native dropdown
    # widget (Greenhouse's React Select). Returning None means "not handled
    # here" so the caller can flag the interaction as failed.
    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        return False

    def _custom_field_is_empty(self, container, widget_type: str) -> bool | None:
        """Optional override for auditing an ATS-specific widget_type's
        current value. Return None to defer to the generic check."""
        return None

    # ------------------------------------------------------------------
    # Shared: screenshots, confidence, telemetry
    # ------------------------------------------------------------------

    def _capture_screenshot(self, name: str):
        if not self.execution_dir:
            return
        try:
            path = os.path.join(self.execution_dir, name)
            self.active_context.locator("body").first.page.screenshot(path=path) if hasattr(self.active_context, "locator") else self.page.screenshot(path=path)
        except Exception:
            try:
                self.page.screenshot(path=os.path.join(self.execution_dir, name))
            except Exception:
                pass

    def _human_type(self, locator, text: str, clear_first: bool = True) -> str:
        """
        Types character-by-character with randomized inter-keystroke delay,
        the way a real person types — as opposed to `.fill()`, which sets a
        field's value instantly in one DOM operation with no keyboard events
        at all. Returns the field's final value so callers can verify it
        the same way they would after a `.fill()`.
        """
        try:
            if clear_first:
                locator.fill("")
            locator.click(timeout=3000)
        except Exception:
            pass
        for ch in text:
            try:
                locator.type(ch, delay=random.randint(40, 140))
            except Exception:
                # Fall back to a plain fill for whatever's left rather than
                # leaving the field partially typed.
                try:
                    locator.fill(text)
                except Exception:
                    pass
                break
        self.page.wait_for_timeout(random.randint(80, 220))
        try:
            return locator.input_value()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Shared: generic widget interaction (standard HTML controls only)
    # ------------------------------------------------------------------

    def _click_and_verify_checked(self, input_locator, fallback_click_target=None) -> bool:
        try:
            input_locator.click(force=True, timeout=3000)
        except Exception:
            pass
        try:
            if input_locator.is_checked():
                return True
        except Exception:
            pass
        # Some custom widgets need the visible label/span clicked rather
        # than the (often visually hidden) native input itself.
        if fallback_click_target is not None:
            try:
                fallback_click_target.click(force=True, timeout=3000)
                return input_locator.is_checked()
            except Exception:
                return False
        return False

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        if widget_type == "native_select":
            interaction["Selector Used"] = "select"
            interaction["Interaction Method"] = "select_option"
            select_loc = container.locator("select")
            try:
                select_loc.first.select_option(label=answer)
            except Exception:
                select_loc.first.select_option(value=answer)
            select_loc.first.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
            return True

        if widget_type == "textarea":
            interaction["Selector Used"] = "textarea"
            interaction["Interaction Method"] = "type() (human-paced)"
            ta = container.locator("textarea").first
            val = self._human_type(ta, answer)
            if val != answer:
                interaction["Interaction Method"] = "fill() (typing fallback)"
                ta.fill(answer)
                val = ta.input_value()
            return val == answer

        if widget_type == "input":
            interaction["Selector Used"] = "input:not([type='hidden'])"
            inp = container.locator('input:not([type="hidden"])').first
            if inp.count() == 0:
                return False
            if inp.get_attribute("maxlength") == "1" and len(answer) > 1:
                interaction["Interaction Method"] = "fill() (segmented input)"
                all_inps = container.locator('input:not([type="hidden"])')
                for i in range(min(all_inps.count(), len(answer))):
                    all_inps.nth(i).fill(answer[i])
                    self.page.wait_for_timeout(50)
                return True
            interaction["Interaction Method"] = "type() (human-paced)"
            val = self._human_type(inp, answer)
            if val != answer:
                interaction["Interaction Method"] = "fill() (typing fallback)"
                inp.fill(answer)
                val = inp.input_value()
            return val == answer

        if widget_type in ["radio_group", "checkbox_group"]:
            interaction["Selector Used"] = "label containing answer"
            interaction["Interaction Method"] = "click()"
            # .check() asserts the "checked" DOM property flips synchronously
            # after the click, which some React-controlled radio/checkbox
            # widgets don't satisfy (state updates via a re-render instead) —
            # click the element a real user would click and verify the
            # resulting state directly instead of trusting that assertion.
            if widget_type == "checkbox_group" and answer in ["True", "Yes"]:
                chk = container.locator('input[type="checkbox"]').first
                if chk.count() > 0:
                    return self._click_and_verify_checked(chk.first)
            labels = container.locator("label").all()
            for lbl in labels:
                if answer.lower() in lbl.inner_text().lower():
                    inp = lbl.locator("input")
                    if inp.count() == 0:
                        for_id = lbl.get_attribute("for")
                        if for_id:
                            inp = container.locator(f'input[id="{for_id}"]')
                    if inp.count() > 0:
                        return self._click_and_verify_checked(inp.first, fallback_click_target=lbl)
            return False

        return self._interact_custom_dropdown(container, answer, interaction)

    # ------------------------------------------------------------------
    # Shared: process custom questions (classification -> answer -> fill)
    # ------------------------------------------------------------------

    def _process_custom_fields(self, telemetry: dict) -> bool:
        logger.info(f"{self.ATS_NAME}Handler: Processing custom fields...")
        safe_to_submit = True

        if "interaction_log" not in telemetry:
            telemetry["interaction_log"] = []

        questions = self._extract_questions()

        for q in questions:
            clean_label = q["question"]
            is_required = q["is_required"]
            widget_type = q["widget_type"]
            options = q["options"]
            placeholder = q["placeholder"]
            container = q["container"]
            label_text = q["raw_label"]

            field_type = "text"
            if widget_type in ["react_select", "native_select", "radio_group"]:
                field_type = "dropdown"
            elif widget_type == "checkbox_group":
                field_type = "multiselect"
            elif widget_type == "textarea":
                field_type = "textarea"

            dom_meta = {
                "css_selector": "", "input_tag": widget_type, "visible": True,
                "disabled": False, "current_value": "", "widget_type": widget_type,
            }

            # Every keyword classifier downstream (this one, and both used
            # inside QuestionEngine.answer()) is English-only. Translate
            # once here so a non-English question (real, live examples this
            # session: French/Swedish Recruitee/Teamtailor postings) is
            # actually recognized as the ordinary field it is instead of
            # escalating just because the text doesn't match an English
            # keyword. telemetry/logging still shows the original text —
            # only the classification/answer inputs are translated.
            clf_label = translate_to_english(clean_label, self.engine.llm_client)
            clf_raw_label = translate_to_english(label_text, self.engine.llm_client)

            classification = QuestionClassifier.classify(clf_label, widget_type)
            if classification == "ESCALATE":
                # Only a REQUIRED escalated question should block the whole
                # submission. An optional one (an open-ended "anything else
                # you'd like us to know?" box, an optional cover letter) is
                # left blank and skipped — same treatment the unanswerable-but-
                # optional path below already gives, and for the same reason:
                # blocking an entire application over a blank optional textarea
                # defeats the point of automating it. The no-guessing-on-
                # required-fields rule is untouched.
                if is_required:
                    logger.info(f"{self.ATS_NAME}Handler: Escalating REQUIRED complex question '{clean_label}' -> REVIEW_REQUIRED")
                    safe_to_submit = False
                else:
                    logger.info(f"{self.ATS_NAME}Handler: Escalated question '{clean_label}' is optional — leaving blank, continuing.")
                telemetry.setdefault("escalated_questions", []).append(
                    {"question": clean_label, "required": is_required}
                )
                continue

            # QuestionEngine.answer() is a large, LLM/RAG-backed code path
            # with no exception handling of its own around most of its
            # branches (confirmed: a missing/failing import inside its date-
            # parsing branch previously took down an entire application with
            # a bare FAILED, rather than just that one field, since nothing
            # between here and execute()'s outermost handler caught it).
            # Treat any exception the same as the existing "unanswerable"
            # path just below — required blocks submission, optional gets
            # skipped — instead of letting one bad question crash the whole
            # run.
            try:
                answer = self.engine.answer(
                    question=clf_label, field_type=field_type, placeholder=placeholder,
                    options=options, label_text=clf_raw_label, required=is_required, dom_meta=dom_meta,
                )
            except Exception as answer_err:
                logger.info(f"{self.ATS_NAME}Handler: engine.answer() raised for '{clean_label}': {answer_err}")
                answer = "REVIEW_REQUIRED"
                dom_meta["confidence"] = 0
                dom_meta["answer_exception"] = str(answer_err)

            # An unanswerable REQUIRED question must block submission — we
            # don't guess. An unanswerable OPTIONAL one (no stored data, low
            # confidence, failed normalization) should just be left blank
            # and skipped instead: blocking the whole application over an
            # empty optional field like a personal portfolio URL is overly
            # conservative and defeats the point of automating this at all.
            conf = dom_meta.get("confidence", 100)
            unanswerable = answer in ["NORMALIZATION_FAILED", "REVIEW_REQUIRED"] or conf < 70
            if unanswerable:
                telemetry.setdefault("missing_fields", []).append(
                    {"type": "PROFILE_MISSING_FIELD", "question": clean_label,
                     "confidence": conf, "required": is_required}
                )
                if is_required:
                    logger.info(f"Validation Error: Answer for '{clean_label}' unanswerable (confidence {conf}). Required field — aborting interaction.")
                    safe_to_submit = False
                else:
                    logger.info(f"Answer for '{clean_label}' unanswerable (confidence {conf}) but optional — leaving blank, continuing.")
                continue

            if not answer:
                continue

            telemetry["question_count"] += 1
            last_log = self.engine.audit_log[-1] if self.engine.audit_log else {}
            if last_log.get("source") == "LLM":
                telemetry["llm_question_count"] += 1
            else:
                telemetry["profile_question_count"] += 1

            interaction = {
                "Question": clean_label, "Expected Value": answer, "Selector Used": "",
                "Interaction Method": "", "Verification Result": False,
            }
            try:
                selection_success = self._interact_widget(widget_type, container, answer, interaction)
                interaction["Verification Result"] = selection_success
                if not selection_success:
                    safe_to_submit = False
            except Exception as e:
                interaction["Verification Result"] = False
                interaction["Error"] = str(e)
                safe_to_submit = False

            telemetry["interaction_log"].append(interaction)

        return safe_to_submit

    # ------------------------------------------------------------------
    # Shared: pre-submit audit
    # ------------------------------------------------------------------

    def _pre_submit_audit(self) -> bool:
        logger.info(f"{self.ATS_NAME}Handler: Running Pre-Submit Audit...")
        safe = True
        missing_count = 0

        for q in self._extract_questions():
            if not q["is_required"]:
                continue
            container = q["container"]
            label_text = q["question"]
            widget_type = q["widget_type"]

            label_lower = label_text.lower()
            if any(kw in label_lower for kw in ["security code", "verification code", "otp", "enter the 8-character code"]):
                continue

            try:
                custom_empty = self._custom_field_is_empty(container, widget_type)
                if custom_empty is not None:
                    if custom_empty:
                        logger.info(f"Pre-Submit Audit Failed: Empty required field near '{label_text}'")
                        safe = False
                        missing_count += 1
                    continue

                if widget_type == "input":
                    for el in container.locator('input:not([type="hidden"])').all():
                        if el.is_visible() and not el.input_value():
                            safe = False
                            missing_count += 1
                elif widget_type == "textarea":
                    for el in container.locator("textarea").all():
                        if el.is_visible() and not el.input_value():
                            safe = False
                            missing_count += 1
                elif widget_type == "native_select":
                    for el in container.locator("select").all():
                        if el.is_visible() and not el.input_value():
                            safe = False
                            missing_count += 1
                elif widget_type in ["radio_group", "checkbox_group"]:
                    inputs = container.locator("input")
                    checked = any(inputs.nth(i).is_checked() for i in range(inputs.count()))
                    if not checked:
                        safe = False
                        missing_count += 1
            except Exception as e:
                logger.info(f"Pre-Submit Audit Warning near label: {e}")

        if missing_count > 0:
            logger.info(f"{self.ATS_NAME}Handler: ABORTING SUBMISSION. Detected {missing_count} empty required fields!")
            return False
        return safe

    # ------------------------------------------------------------------
    # Shared: OTP handling (generic — reuses the same Gmail IMAP retriever
    # regardless of which ATS triggered the challenge)
    # ------------------------------------------------------------------

    def _check_for_otp(self) -> bool:
        try:
            ctx = self.active_context
            if ctx.locator('fieldset#email-verification, input[id^="security-input-"]').count() > 0:
                return True
            if ctx.locator('text="Verify Email", text="Enter Code", text="One-Time Password", text="OTP", text="Verification Code"').first.is_visible(timeout=1000):
                return True
            inputs = ctx.locator('input[maxlength="1"]').all()
            if len(inputs) in [6, 8]:
                return True
            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Shared: CAPTCHA handling (human-in-the-loop, not automated solving —
    # see the comment on _wait_for_human_captcha_resolution for why)
    # ------------------------------------------------------------------

    # Lives on the base class deliberately, not any one ATS's handler: every
    # subclass (the 3 built so far, and every future one) shares this exact
    # execute() state machine and gets captcha handling for free just by
    # existing — no per-platform reimplementation needed. Vendor list is
    # intentionally broader than what's been directly observed (hCaptcha on
    # Lever, reCAPTCHA on Ashby/Greenhouse, both confirmed live this
    # session) — Workday/SmartRecruiters/iCIMS/etc. haven't been built yet,
    # and different ATSs commonly use different anti-bot vendors.
    _CAPTCHA_CHALLENGE_FRAME_SELECTOR = (
        'iframe[title*="challenge" i], iframe[src*="bframe"], '
        'iframe[src*="recaptcha/api2/bframe"], iframe[src*="recaptcha/enterprise/bframe"], '
        'iframe[src*="challenges.cloudflare.com"], iframe[src*="arkoselabs"], '
        'iframe[title*="arkose" i], iframe[src*="funcaptcha"], iframe[src*="geetest"]'
    )
    _CAPTCHA_WIDGET_SELECTOR = (
        '.h-captcha, [data-hcaptcha-widget-id], iframe[src*="recaptcha"], iframe[src*="hcaptcha"], '
        '.cf-turnstile, iframe[src*="turnstile"], #fc-iframe-wrap, [id*="funcaptcha" i], '
        '.geetest_holder, [class*="geetest" i], iframe[title*="captcha" i], iframe[src*="captcha" i]'
    )

    def _check_for_captcha_challenge(self) -> bool:
        """Detects a captcha that likely needs a human: either a visibly
        active challenge (hCaptcha's drag-the-icon puzzle, reCAPTCHA's
        image grid — confirmed present on a real Lever posting this
        session) rendered in its own iframe, or just a captcha widget
        present on a page where the submit didn't go through cleanly
        (covers Ashby/Greenhouse's invisible/silent-fail reCAPTCHA variant,
        also confirmed this session — no visible challenge ever appears,
        but the actual submit request never fires either).

        Only meaningful to call right after an ambiguous/failed submit —
        every one of these ATSs has a captcha widget present from page
        load, so this isn't a "is a captcha here at all" check, it's a
        "is a captcha the likely reason this submit didn't go through"
        check, made by the caller at the right point in the flow.
        """
        try:
            challenge_frame = self.page.locator(self._CAPTCHA_CHALLENGE_FRAME_SELECTOR)
            for i in range(challenge_frame.count()):
                if challenge_frame.nth(i).is_visible():
                    return True
            return self.page.locator(self._CAPTCHA_WIDGET_SELECTOR).count() > 0
        except Exception:
            return False

    def _wait_for_human_captcha_resolution(self, telemetry: dict) -> bool:
        """Pauses and hands the (visible, non-headless — see
        LaunchedBrowser) browser window to a human operator to solve the
        captcha themselves, then blocks on their signal to continue.

        This is deliberately NOT automated captcha solving. A real person
        clearing the challenge is the actual thing these systems are
        designed to allow; defeating the check programmatically (a
        solving service, a custom solver, scripting past it) is not
        something this system does. What automation can legitimately do
        is everything around that one moment — fill every field, answer
        every question, get the form to exactly the point where a human's
        few seconds of attention is the only thing left — then get out of
        the way and let them provide it.

        Returns True if the operator signaled the challenge is resolved,
        False if they signaled giving up on this one (routes to
        REVIEW_REQUIRED same as any other unresolved blocker).
        """
        telemetry["captcha_paused"] = True
        telemetry.setdefault("captcha_pause_count", 0)
        telemetry["captcha_pause_count"] += 1
        self._capture_screenshot(f"captcha_pause_{telemetry['captcha_pause_count']}.png")
        logger.info(f"{self.ATS_NAME}Handler: >>> CAPTCHA detected — browser window is open, please solve it now. <<<")
        logger.info(f"{self.ATS_NAME}Handler: Press Enter here once solved (or type 'skip' to send this one to review instead): ")
        try:
            response = input().strip().lower()
        except Exception:
            response = "skip"
        resolved = response != "skip"
        telemetry["captcha_resolution"] = "resolved" if resolved else "skipped"
        if resolved:
            logger.info(f"{self.ATS_NAME}Handler: Resuming — will retry submit now.")
        return resolved

    def _post_otp_analysis(self) -> dict:
        analysis = {"current_url": self.page.url, "page_title": self.page.title(),
                    "visible_headers": [], "validation_errors": [], "required_fields_remaining": 0}
        try:
            for h in self.active_context.locator("h1, h2, h3").all():
                if h.is_visible():
                    analysis["visible_headers"].append(h.inner_text().strip())
            for err in self.active_context.locator(".error-message, .field_with_errors").all():
                if err.is_visible():
                    analysis["validation_errors"].append(err.inner_text().strip())
            inputs = self.active_context.locator('input[aria-required="true"], select[aria-required="true"], textarea[aria-required="true"]').all()
            for inp in inputs:
                if inp.is_visible() and not inp.input_value():
                    analysis["required_fields_remaining"] += 1
        except Exception as e:
            analysis["error"] = str(e)

        if self.execution_dir:
            import json
            with open(os.path.join(self.execution_dir, "otp_forensics.json"), "w") as f:
                json.dump(analysis, f, indent=4)
        return analysis

    def _handle_otp(self, telemetry: dict) -> str:
        self._capture_screenshot("02_otp_page.png")
        logger.info(f"{self.ATS_NAME}Handler: Entering OTP_RETRIEVING state.")
        telemetry["otp_detected"] = True

        start_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        code = None
        cumulative_wait = 0

        for delay in [10, 20, 40]:
            logger.info(f"{self.ATS_NAME}Handler: Fetching OTP... (Wait: {delay}s)")
            self.page.wait_for_timeout(delay * 1000)
            cumulative_wait += delay
            result = retrieve_application_otp(start_time)
            telemetry["otp_forensics_v2"] = result
            telemetry["otp_forensics_v2"]["waited_seconds"] = cumulative_wait
            if result.get("code"):
                code = result["code"]
                break

        if not code:
            logger.info(f"{self.ATS_NAME}Handler: OTP Retrieval Failed after max retries.")
            telemetry["otp_received"] = False
            return WorkflowState.OTP_REQUIRED.name

        telemetry["otp_received"] = True
        logger.info(f"{self.ATS_NAME}Handler: OTP Retrieved -> {code}. Entering OTP_SUBMITTED state.")

        try:
            inputs = self.active_context.locator('input:not([type="hidden"])').all()
            split_inputs = [inp for inp in inputs if inp.get_attribute("maxlength") == "1"]
            if len(split_inputs) == len(code):
                for i in range(len(code)):
                    split_inputs[i].fill(code[i])
                    self.page.wait_for_timeout(50)
            else:
                for inp in inputs:
                    if inp.is_visible():
                        inp.fill(code)
                        break
            telemetry["otp_submitted"] = True
            self._capture_screenshot("03_after_otp_filled.png")
            logger.info(f"{self.ATS_NAME}Handler: OTP Filled. Awaiting submit...")
            return "OTP_SUBMITTED"
        except Exception as e:
            logger.info(f"{self.ATS_NAME}Handler: Error filling OTP: {e}")
            return WorkflowState.REVIEW_REQUIRED.name

    # ------------------------------------------------------------------
    # Shared: main state machine
    # ------------------------------------------------------------------

    def execute(self) -> dict:
        telemetry = {
            "question_count": 0, "llm_question_count": 0, "profile_question_count": 0,
            "filled_fields": {"Resume": False, "Email": False, "Phone": False, "LinkedIn": False,
                               "Questions": False, "Attachments": False},
        }
        self.telemetry = telemetry

        try:
            self._enter_application_flow()
            self._detect_and_set_iframe()
            self._capture_screenshot("01_page_loaded.png")

            if not self._fill_and_verify_standard_fields():
                logger.info(f"{self.ATS_NAME}Handler: Standard field validation failed. Safety Pause.")
                self._capture_screenshot("05_pre_submit.png")
                return {"status": WorkflowState.REVIEW_REQUIRED.name, "audit_log": self.engine.audit_log, "telemetry": telemetry}

            self._capture_screenshot("03_profile_completed.png")
            if not self._upload_resume():
                logger.info(f"{self.ATS_NAME}Handler: Resume upload failed after retries. Aborting.")
                self._capture_screenshot("03b_resume_upload_failed.png")
                return {"status": WorkflowState.REVIEW_REQUIRED.name, "audit_log": self.engine.audit_log, "telemetry": telemetry}

            self._capture_screenshot("02_resume_uploaded.png")
            result_status = WorkflowState.FAILED.name

            cycles = 0
            while cycles < 10:
                cycles += 1
                attempt = cycles - 1
                logger.info(f"{self.ATS_NAME}Handler: Starting cycle {cycles}/10...")

                safe_to_submit = self._process_custom_fields(telemetry)
                self._capture_screenshot(f"04_questions_completed_attempt_{attempt}.png")

                if safe_to_submit:
                    safe_to_submit = self._pre_submit_audit()

                if not safe_to_submit:
                    logger.info(f"{self.ATS_NAME}Handler: Safety rules triggered. Moving to REVIEW_REQUIRED.")
                    self._capture_screenshot("05_pre_submit.png")
                    result_status = WorkflowState.REVIEW_REQUIRED.name
                    break

                logger.info(f"{self.ATS_NAME}Handler: All checks passed. AUTO-SUBMITTING (Attempt {attempt + 1}).")
                if self.test_mode:
                    logger.info(f"{self.ATS_NAME}Handler: TEST MODE ACTIVE. Skipping final submit.")
                    self._capture_screenshot("05_pre_submit.png")
                    result_status = WorkflowState.COMPLETED.name
                    telemetry["submission_proof"] = {
                        "url": self.page.url, "title": self.page.title(),
                        "success_text": "TEST MODE SUCCESS", "screenshot": "05_pre_submit.png",
                    }
                    break

                submit_btn = self._get_submit_button_locator()
                is_disabled = False
                try:
                    is_disabled = submit_btn.is_disabled() or submit_btn.get_attribute("aria-disabled") == "true"
                except Exception:
                    pass

                if self._check_for_otp():
                    logger.info(f"{self.ATS_NAME}Handler: Verification -> OTP_REQUIRED (Detected before click)")
                    otp_status = self._handle_otp(telemetry)
                    if otp_status == "OTP_SUBMITTED":
                        submit_btn = self._get_submit_button_locator()
                        is_disabled = False
                    else:
                        result_status = otp_status
                        break

                if is_disabled:
                    logger.info(f"{self.ATS_NAME}Handler: Submit button is DISABLED. Aborting to REVIEW_REQUIRED.")
                    result_status = WorkflowState.REVIEW_REQUIRED.name
                    break

                # Click submit. If an OTP challenge appears AFTER this click, fill it
                # and click again immediately within this same cycle — do not fall
                # back to the outer `while` loop, which would re-extract and re-answer
                # every custom question from scratch before ever attempting a second
                # click, risking the OTP going stale (or the questions changing) before
                # resubmission actually happens.
                verification = None
                otp_after_click_failed = False
                for click_attempt in range(3):
                    try:
                        self._capture_screenshot("01_before_submit.png")
                        telemetry["submit_clicked"] = True
                        try:
                            submit_btn.click(timeout=10000)
                        except Exception as intercept_err:
                            # A passive/invisible CAPTCHA widget's container
                            # div can occupy DOM space that visually overlaps
                            # the submit button (e.g. Lever's hCaptcha),
                            # which Playwright's strict actionability check
                            # refuses to click through even though nothing
                            # is actually blocking the click a real user
                            # would make. Retrying with force=True only
                            # bypasses that pointer-interception check — it
                            # does not fabricate or bypass a real captcha
                            # token; if the challenge genuinely required
                            # solving, the submission still fails downstream
                            # and SubmissionVerifier catches it normally.
                            if "intercepts pointer events" not in str(intercept_err):
                                raise
                            logger.info(f"{self.ATS_NAME}Handler: Submit click intercepted (likely a passive CAPTCHA overlay) — retrying with force=True.")
                            submit_btn.click(timeout=10000, force=True)
                        logger.info(f"{self.ATS_NAME}Handler: Submit button clicked. Waiting for processing...")
                        try:
                            self.page.wait_for_load_state("networkidle", timeout=7000)
                        except Exception:
                            pass
                        self.page.wait_for_timeout(2000)
                    except Exception as click_err:
                        logger.info(f"{self.ATS_NAME}Handler: Submit click failed: {click_err}")
                        result_status = WorkflowState.FAILED.name
                        verification = None
                        break

                    verification = SubmissionVerifier.verify(self.page, self.ATS_NAME, active_context=self.active_context)
                    telemetry["submission_proof"] = verification["proof"]

                    if verification["status"] == "SUBMITTED_CONFIRMED":
                        logger.info(f"{self.ATS_NAME}Handler: Verification -> SUCCESS (Confidence: {verification['confidence']}%)")
                        self._capture_screenshot("06_post_submit.png")
                        result_status = WorkflowState.COMPLETED.name
                        # The only place this becomes True: a real (non-test_mode)
                        # submit click that the verifier independently confirmed
                        # via a real success signal. WorkflowState.COMPLETED alone
                        # is ambiguous — test_mode also reaches COMPLETED without
                        # ever clicking submit — so anything reporting "was this
                        # job actually submitted?" must check this flag, not just
                        # the status string.
                        telemetry["really_submitted"] = True
                        break

                    if self._check_for_otp():
                        otp_status = self._handle_otp(telemetry)
                        if otp_status != "OTP_SUBMITTED":
                            result_status = otp_status
                            verification = None
                            otp_after_click_failed = True
                            break
                        submit_btn = self._get_submit_button_locator()
                        try:
                            still_disabled = submit_btn.is_disabled() or submit_btn.get_attribute("aria-disabled") == "true"
                        except Exception:
                            still_disabled = False
                        if still_disabled:
                            logger.info(f"{self.ATS_NAME}Handler: Submit button still DISABLED after OTP fill. Aborting to REVIEW_REQUIRED.")
                            result_status = WorkflowState.REVIEW_REQUIRED.name
                            verification = None
                            otp_after_click_failed = True
                            break
                        # Loop back within THIS cycle to click again — OTP is now filled.
                        continue

                    if self._check_for_captcha_challenge():
                        if self._wait_for_human_captcha_resolution(telemetry):
                            submit_btn = self._get_submit_button_locator()
                            # Loop back within THIS cycle to click again — a
                            # human just cleared the captcha in the live
                            # browser window.
                            continue
                        result_status = WorkflowState.REVIEW_REQUIRED.name
                        verification = None
                        break

                    # Submitted, no confirmation, no OTP challenge, no captcha —
                    # fall through to the generic failure handling below using
                    # this `verification`.
                    break
                else:
                    logger.info(f"{self.ATS_NAME}Handler: Exhausted submit/OTP/captcha retries within cycle. Aborting to REVIEW_REQUIRED.")
                    result_status = WorkflowState.REVIEW_REQUIRED.name
                    verification = None

                if result_status == WorkflowState.COMPLETED.name:
                    break
                if verification is None:
                    if otp_after_click_failed:
                        break
                    if result_status == WorkflowState.FAILED.name:
                        break
                    result_status = WorkflowState.REVIEW_REQUIRED.name
                    break

                if verification["status"] == "FAILED_RECOVERABLE" or verification["proof"].get("failure_signals_found", 0) > 0:
                    self._capture_screenshot(f"05_post_submit_failure_{attempt}.png")
                    if telemetry.get("submit_clicked"):
                        logger.info(f"{self.ATS_NAME}Handler: Verification -> VALIDATION_ERROR. Rule 1 Enforced: NEVER RESUBMIT. Aborting.")
                        result_status = WorkflowState.REVIEW_REQUIRED.name
                        break
                    continue

                logger.info(f"{self.ATS_NAME}Handler: Verification -> {verification['status']} detected: {verification['proof'].get('error_text')}")
                self._capture_screenshot(f"05_post_submit_failure_{attempt}.png")
                result_status = WorkflowState.REVIEW_REQUIRED.name
                break
            else:
                logger.info(f"{self.ATS_NAME}Handler: Maximum retry attempts reached. Moving to REVIEW_REQUIRED.")
                result_status = WorkflowState.REVIEW_REQUIRED.name

            self._capture_screenshot("05_final_page.png")
            return {"status": result_status, "audit_log": self.engine.audit_log, "telemetry": telemetry}

        except Exception as e:
            logger.info(f"{self.ATS_NAME}Handler Execution Error: {e}")
            return {"status": WorkflowState.FAILED.name, "error": str(e), "audit_log": self.engine.audit_log, "telemetry": telemetry}
