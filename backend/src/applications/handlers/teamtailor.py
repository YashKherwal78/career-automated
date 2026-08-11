from src.system.logger import setup_logger
logger = setup_logger('teamtailor')
import os
import re
from src.applications.handlers.base_handler import BaseATSHandler

class TeamTailorHandler(BaseATSHandler):
    """
    Teamtailor postings render in the tenant's own locale (French, Swedish,
    etc.), so the "Apply"/"Rejoindre l'équipe" call-to-action button is
    matched by its stable Stimulus.js `data-action` hook
    (`...#showFormOverlay`), never by display text. A cookie-consent
    banner also intercepts clicks until dismissed, same as other EU-hosted
    platforms this session.

    Every field — standard and tenant-custom — uses a real
    `<label for="candidate_...">` tied to a Rails-style bracket-named
    input (`candidate[first_name]`, `candidate[answers_attributes][N][...]`
    for custom questions), so labels resolve directly with no DOM-
    proximity guessing.
    """
    ATS_NAME = "TEAMTAILOR"

    _STANDARD_IDS = {
        "candidate_first_name", "candidate_last_name", "candidate_email", "candidate_phone",
        "candidate_resume_remote_url", "candidate_file_remote_url", "candidate_consent_given",
    }

    def _enter_application_flow(self):
        logger.info("TeamTailorHandler: Entering application flow...")
        try:
            cookie_btn = self.page.get_by_role("button", name=re.compile("accept|accepter|godkänn|akzeptieren", re.I)).first
            if cookie_btn.count() > 0 and cookie_btn.is_visible():
                cookie_btn.click(timeout=5000)
                self.page.wait_for_timeout(500)
        except Exception as e:
            logger.info(f"TeamTailorHandler: Cookie consent dismiss skipped/failed (non-fatal): {e}")

        try:
            self.page.wait_for_selector('#candidate_first_name', timeout=2000)
            return
        except Exception:
            pass
        try:
            apply_btn = self.page.locator('button[data-action*="showFormOverlay"]').first
            if apply_btn.count() == 0:
                apply_btn = self.page.get_by_role("button", name=re.compile("apply|postuler|rejoindre|ansök", re.I)).first
            apply_btn.click(timeout=8000)
            self.page.wait_for_selector('#candidate_first_name', timeout=10000)
        except Exception as e:
            logger.info(f"TeamTailorHandler: Apply click failed or form still not found: {e}")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("TeamTailorHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "candidate_first_name": self.profile.get_field("first_name"),
            "candidate_last_name": self.profile.get_field("last_name"),
            "candidate_email": self.profile.get_field("email"),
            "candidate_phone": self.profile.get_field("phone"),
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = self.active_context.locator(f'#{field_id}').first
            if el.count() == 0:
                continue
            try:
                self._human_type(el, val)
                self.page.wait_for_timeout(150)
                if not el.input_value():
                    logger.info(f"TeamTailorHandler: CRITICAL - Field {field_id} failed to populate.")
                    safe_to_proceed = False
                elif field_id == "candidate_email":
                    self.telemetry.setdefault("filled_fields", {})["Email"] = True
                elif field_id == "candidate_phone":
                    self.telemetry.setdefault("filled_fields", {})["Phone"] = True
            except Exception as e:
                logger.info(f"TeamTailorHandler: Error filling {field_id}: {e}")
                safe_to_proceed = False

        # Required data-processing consent checkbox, handled directly
        # rather than through the generic question pipeline — Teamtailor
        # postings render in the tenant's own locale (French here), and
        # the shared question classifier's keyword lists are English-only,
        # so a French "je consens à ce que 2LCollection stocke mes
        # données..." checkbox doesn't match any PRIVACY_ACK/consent
        # keyword and gets escalated on every single non-English posting.
        # A required, single (non-grouped) checkbox tied to a privacy/
        # data-processing paragraph is the same fixed "always consent"
        # pattern every other platform's own GDPR checkbox already gets
        # (Ashby, Breezy, BambooHR, Recruitee) — language-independent by
        # construction since it doesn't route through text classification.
        consent_el = self.active_context.locator('#candidate_consent_given').first
        if consent_el.count() > 0:
            if not self._click_and_verify_checked(consent_el):
                logger.info("TeamTailorHandler: CRITICAL - Could not check required data-processing consent.")
                safe_to_proceed = False

        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"TeamTailorHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        file_input = self.active_context.locator('#candidate_resume_remote_url').first
        if file_input.count() == 0:
            file_input = self.active_context.locator('input[type="file"]').first
        if file_input.count() == 0:
            logger.info("TeamTailorHandler: No file input found for resume upload.")
            return False

        try:
            file_input.set_input_files(self.resume_path, timeout=8000)
        except Exception as e:
            logger.info(f"TeamTailorHandler: set_input_files failed: {e}")
            return False

        resume_base = os.path.splitext(os.path.basename(self.resume_path))[0]
        try:
            self.active_context.wait_for_selector(f"text={resume_base}", timeout=8000)
            logger.info("  -> Upload Verified: True")
        except Exception:
            try:
                self.active_context.wait_for_selector('text=/remove|delete|supprimer/i', timeout=4000)
                logger.info("  -> Upload Verified: True (via Remove/Delete indicator)")
            except Exception:
                logger.info("  -> Upload Verified: False (Could not verify DOM)")
                self._capture_screenshot("resume_verification_failure.png")
                return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        logger.info("TeamTailorHandler: Extracting custom questions...")
        questions = []
        labels = self.active_context.locator("label[for]").all()

        for label_loc in labels:
            try:
                if not label_loc.is_visible():
                    continue
                for_id = label_loc.get_attribute("for") or ""
                if for_id in self._STANDARD_IDS:
                    continue

                target = self.active_context.locator(f'#{for_id}').first
                if target.count() == 0:
                    continue
                typ = (target.get_attribute("type") or "").lower()
                if typ == "file":
                    continue

                # Teamtailor renders a separate "Requis"/"Required" hint
                # as its own line inside the same <label> — and its
                # position isn't consistent: the date question has it
                # AFTER the question text, but the GDPR consent checkbox
                # has it BEFORE, so blindly taking the first line grabbed
                # "Requis." as the entire question on that field. Filter
                # every required-hint-only line out and take the first
                # remaining substantive one instead.
                all_lines = [l.strip() for l in label_loc.inner_text().split("\n") if l.strip()]
                content_lines = [l for l in all_lines if l.rstrip(".*").strip().lower() not in ("requis", "required")]
                raw_text = (content_lines[0] if content_lines else (all_lines[0] if all_lines else "")).strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label:
                    continue
                full_label_text = label_loc.inner_text().lower()
                is_required = "*" in raw_text or "requis" in full_label_text or "required" in full_label_text

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
                elif typ == "date":
                    widget_type = "input"
                    # This is a real native <input type="date">, which
                    # requires ISO "yyyy-mm-dd" for .fill() regardless of
                    # what locale-formatted string the browser visually
                    # displays (French UI shows dd/mm/yyyy) — hint the
                    # format the field actually needs, not the display
                    # convention, so the normalizer produces a value the
                    # native picker will actually accept.
                    placeholder = "yyyy-mm-dd"
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

        logger.info(f"TeamTailorHandler: Detected {len(questions)} custom questions.")
        return questions

    def _interact_widget(self, widget_type: str, container, answer: str, interaction: dict) -> bool:
        # Labels are linked via `for`, not by wrapping the field, so
        # "container" here is always the raw input/select/textarea itself
        # — interact with it directly rather than searching its
        # (nonexistent) descendants.
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
            if widget_type == "native_select":
                return not container.input_value()
            return not container.input_value().strip()
        except Exception:
            return True

    def _get_submit_button_locator(self):
        return self.page.locator('input[type="submit"][name="commit"]').first
