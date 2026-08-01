from src.system.logger import setup_logger
logger = setup_logger('greenhouse')
import re
import os
from src.applications.handlers.base_handler import BaseATSHandler

class GreenhouseHandler(BaseATSHandler):
    ATS_NAME = "GREENHOUSE"

    def _calculate_form_confidence(self, context) -> int:
        score = 0
        try:
            if context.locator('input#first_name, input[name="first_name"]').count() > 0:
                score += 40
            if context.locator('input[type="file"]').count() > 0:
                score += 30
            if context.locator('button[type="submit"], #submit_app').count() > 0:
                score += 40
            if context.locator('.error-message, .field_with_errors').count() > 0:
                score += 25
        except Exception:
            pass
        return score

    def _enter_application_flow(self):
        logger.info("GreenhouseHandler: Entering application flow...")
        score = self._calculate_form_confidence(self.page)
        logger.info(f"  -> Initial Form Confidence Score: {score}")
        if score >= 40:
            logger.info("  -> Application form detected initially. Proceeding.")
            return

        apply_el = self.page.get_by_text("Apply", exact=True).first
        try:
            apply_el.click(timeout=5000)
            self.page.wait_for_timeout(1500)
        except Exception:
            pass

    def _detect_and_set_iframe(self):
        logger.info("GreenhouseHandler: Scanning for iframes...")
        try:
            from urllib.parse import urlparse
            frames = self.page.frames
            logger.info(f"  -> Found {len(frames)} frames.")
            for f in frames:
                logger.info(f"  -> Frame URL: {f.url}")
                if f == self.page.main_frame:
                    continue
                # Check the frame's own hostname, not a raw substring match
                # against the full URL — helper iframes (Google gapi/reCAPTCHA
                # proxies) carry the parent page's URL in a query/hash param
                # (e.g. "...#parent=https%3A%2F%2Fjob-boards.greenhouse.io"),
                # which would falsely match a substring check.
                try:
                    host = urlparse(f.url).hostname or ""
                except Exception:
                    host = ""
                if host.endswith("greenhouse.io"):
                    logger.info(f"GreenhouseHandler: Detected Greenhouse iframe ({f.url}). Promoting to active_context.")
                    self.active_context = f
                    return
        except Exception as e:
            logger.info(f"GreenhouseHandler: Iframe scan error: {e}")
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        logger.info("GreenhouseHandler: Verifying standard fields...")
        safe_to_proceed = True

        fields = {
            "first_name": ['input#first_name', 'input[name="first_name"]'],
            "last_name": ['input#last_name', 'input[name="last_name"]'],
            "email": ['input#email', 'input[name="email"]'],
            "phone": ['input#phone', 'input[name="phone"]']
        }

        for key, locators in fields.items():
            val = self.profile.get_field(key)
            if not val:
                continue

            input_el = None
            for loc in locators:
                if self.active_context.locator(loc).count() > 0:
                    input_el = self.active_context.locator(loc).first
                    break

            if input_el:
                try:
                    current = input_el.input_value()
                    if not current:
                        self._human_type(input_el, val)

                    self.page.wait_for_timeout(200)
                    if not input_el.input_value():
                        logger.info(f"GreenhouseHandler: Field {key} empty after fill. Retrying...")
                        self._human_type(input_el, val)
                        self.page.wait_for_timeout(200)
                        if not input_el.input_value():
                            logger.info(f"GreenhouseHandler: CRITICAL - Field {key} failed to populate.")
                            safe_to_proceed = False
                        elif key == "email" and "filled_fields" in self.telemetry:
                            self.telemetry["filled_fields"]["Email"] = True
                        elif key == "phone" and "filled_fields" in self.telemetry:
                            self.telemetry["filled_fields"]["Phone"] = True
                    else:
                        if key == "email" and "filled_fields" in self.telemetry:
                            self.telemetry["filled_fields"]["Email"] = True
                        elif key == "phone" and "filled_fields" in self.telemetry:
                            self.telemetry["filled_fields"]["Phone"] = True
                except Exception as e:
                    logger.info(f"GreenhouseHandler: Error filling {key}: {e}")
                    safe_to_proceed = False

        # "Country" is a standard field on some tenants' forms — positioned
        # right next to Phone, this is the phone number's country-code
        # selector (a React Select showing "+91 India" style options), not
        # a general "which country do you live in" question (that's the
        # separate "What country do you reside in?" custom question,
        # handled elsewhere). Searching by dial code ("+91") is a more
        # precise, less ambiguous query for this specific widget than the
        # bare country name. _extract_questions() deliberately skips this
        # field under the assumption it's handled here, so it must actually
        # be handled here, not silently left empty.
        dial_code = self.profile.get_field("phone_country_code") or ""
        country_val = self.profile.get_field("country") or ""
        if dial_code or country_val:
            try:
                self.page.wait_for_timeout(300)  # let any async-rendered fields settle
                # Search for the label directly, anywhere in the form, rather
                # than only checking each field container's first label —
                # some tenants nest the Country react-select INSIDE the
                # Phone fieldset (a single <legend>Phone</legend> wraps both
                # the country-code picker and the number input), so a
                # container-first-label check reads "Phone" and silently
                # misses the nested "Country" field entirely.
                country_label = None
                for lbl in self.active_context.locator('label, legend').all():
                    if not lbl.is_visible():
                        continue
                    text = lbl.inner_text().split("\n")[0].strip().rstrip("*").strip().lower()
                    if text == "country":
                        country_label = lbl
                        break

                if country_label is None:
                    logger.info("GreenhouseHandler: No 'Country' field found on this form — skipping.")
                else:
                    # The label may be tied to its control via `for`/id
                    # rather than DOM nesting, so resolve the control from
                    # the label's `for` attribute first and only fall back
                    # to "nearest ancestor field" if that's absent.
                    for_id = country_label.get_attribute("for")
                    if for_id:
                        control_root = self.active_context.locator(f'label[for="{for_id}"]').locator(
                            "xpath=ancestor::*[contains(@class,'select') or contains(@class,'field')][1]"
                        )
                    else:
                        control_root = country_label.locator("xpath=..")

                    if control_root.count() == 0:
                        control_root = country_label.locator("xpath=..")

                    if control_root.locator('div[class*="select__control"], div[class*="-control"]').count() > 0:
                        if not self._select_country_code_dropdown(control_root, dial_code, country_val):
                            logger.info("GreenhouseHandler: CRITICAL - Country dropdown failed to populate.")
                            safe_to_proceed = False
                    elif control_root.locator("select").count() > 0:
                        try:
                            control_root.locator("select").first.select_option(label=country_val)
                        except Exception:
                            logger.info("GreenhouseHandler: CRITICAL - Country <select> failed to populate.")
                            safe_to_proceed = False
                    else:
                        logger.info("GreenhouseHandler: CRITICAL - Found 'Country' label but no matching control.")
                        safe_to_proceed = False
            except Exception as e:
                logger.info(f"GreenhouseHandler: Error filling Country: {e}")
                safe_to_proceed = False

        return safe_to_proceed

    def _select_country_code_dropdown(self, container, dial_code: str, country_val: str) -> bool:
        """Searches this React Select by dial code (e.g. "+91") and takes
        the top suggestion — a precise, unambiguous query for a phone
        country-code widget, unlike searching by bare country name."""
        rs_loc = container.locator('div[class*="select__control"], div[class*="-control"]')
        rs_loc.first.click(timeout=3000, force=True)
        try:
            self.active_context.locator('div[class*="-option"]').first.wait_for(state="visible", timeout=3000)
        except Exception:
            pass

        inp = rs_loc.first.locator('input')
        query = dial_code or country_val
        if inp.count() > 0:
            self._human_type(inp.first, query, clear_first=True)
            self.page.wait_for_timeout(1200)
            first_suggestion = self.active_context.locator('div[class*="-option"]').first
            if first_suggestion.count() > 0:
                first_suggestion.click(timeout=2000, force=True)

        self.page.wait_for_timeout(300)
        val_el = container.locator('div[class*="select__single-value"]')
        val = val_el.inner_text().strip().lower() if val_el.count() > 0 else ""
        if not val:
            return False
        return (dial_code and dial_code.lower() in val) or (country_val and country_val.lower() in val)

    def _upload_resume(self) -> bool:
        logger.info(f"GreenhouseHandler: Uploading resume {self.resume_path}...")

        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}
        self.telemetry["resume_filename"] = os.path.basename(self.resume_path)
        self.telemetry["resume_upload_success"] = False

        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False

        import shutil
        safe_company = re.sub(r'[^a-zA-Z0-9]', '', self.company_name)
        safe_title = re.sub(r'[^a-zA-Z0-9]', '', self.job_title)
        if not safe_company: safe_company = "Company"
        if not safe_title: safe_title = "Role"

        new_resume_name = f"Resume_{safe_company}_{safe_title}.pdf"

        if self.execution_dir:
            upload_path = os.path.join(self.execution_dir, new_resume_name)
        else:
            upload_path = os.path.join(os.path.dirname(self.resume_path), new_resume_name)

        try:
            shutil.copy2(self.resume_path, upload_path)
            logger.info(f"  -> Renamed to: {new_resume_name}")
        except Exception as e:
            logger.info(f"  -> Rename failed, using original: {e}")
            upload_path = self.resume_path

        file_size = os.path.getsize(upload_path)
        logger.info(f"  -> File Exists: True")
        logger.info(f"  -> File Size: {file_size} bytes")

        for attempt in range(2):
            try:
                import json
                strategy_file = "data/upload_strategies.json"
                known_strategy = None
                if os.path.exists(strategy_file):
                    try:
                        with open(strategy_file, "r") as f:
                            strategies_data = json.load(f)
                            known_strategy = strategies_data.get(self.company_name)
                    except Exception:
                        pass

                upload_success = False

                strategies = [
                    {"name": "A", "desc": "input[type='file']", "loc": 'input[type="file"]'},
                    {"name": "B", "desc": "button (Attach/Upload/Browse)", "loc": 'button:has-text("Attach"), button:has-text("Upload"), button:has-text("Browse")'},
                    {"name": "C", "desc": "label associated with upload", "loc": 'label:has-text("Resume"), label:has-text("CV")'},
                    {"name": "E", "desc": "aria-label search", "loc": '[aria-label*="Upload"], [aria-label*="Resume"], [aria-label*="CV"]'}
                ]

                if known_strategy:
                    strategies = [s for s in strategies if s["name"] == known_strategy] + [s for s in strategies if s["name"] != known_strategy]

                for strat in strategies:
                    logger.info(f"  -> Trying Strategy {strat['name']}: {strat['desc']}")
                    loc = self.active_context.locator(strat['loc']).first
                    if loc.count() > 0:
                        try:
                            if strat['name'] == 'A':
                                loc.set_input_files(upload_path, timeout=5000)
                                upload_success = True
                            else:
                                with self.page.expect_file_chooser(timeout=5000) as fc_info:
                                    loc.click(force=True, timeout=5000)
                                file_chooser = fc_info.value
                                file_chooser.set_files(upload_path)
                                upload_success = True

                            if upload_success:
                                logger.info(f"  -> Strategy {strat['name']} executed successfully.")
                                try:
                                    s_data = {}
                                    if os.path.exists(strategy_file):
                                        with open(strategy_file, "r") as f:
                                            s_data = json.load(f)
                                    s_data[self.company_name] = strat['name']
                                    with open(strategy_file, "w") as f:
                                        json.dump(s_data, f)
                                except Exception:
                                    pass
                                break
                        except Exception as e:
                            logger.info(f"  -> Strategy {strat['name']} failed: {e}")

                if not upload_success:
                    logger.info(f"  -> All upload strategies failed. (Attempt {attempt+1})")
                    if attempt == 0: continue
                    return False

                resume_name_only = os.path.splitext(new_resume_name)[0]

                error_banners = self.active_context.locator('.error-message, .validation-error, [role="alert"]').all_inner_texts()
                if any("resume" in err.lower() or "upload" in err.lower() or "file" in err.lower() for err in error_banners):
                    logger.info(f"  -> Upload Verified: False (Error banner detected). (Attempt {attempt+1})")
                    if attempt == 0: continue
                    return False

                try:
                    self.active_context.wait_for_selector(f"text={resume_name_only}", timeout=8000)
                    logger.info(f"  -> Upload Verified: True")
                    self.telemetry["resume_upload_success"] = True
                    self.telemetry["filled_fields"]["Resume"] = True
                    return True
                except Exception:
                    try:
                        self.active_context.wait_for_selector('button:has-text("Remove"), a:has-text("Remove")', timeout=4000)
                        logger.info(f"  -> Upload Verified: True (via Remove button)")
                        self.telemetry["resume_upload_success"] = True
                        self.telemetry["filled_fields"]["Resume"] = True
                        return True
                    except Exception:
                        logger.info(f"  -> Upload Verified: False (Could not verify DOM). (Attempt {attempt+1})")
                        self._capture_screenshot(f"resume_verification_failure_attempt_{attempt}.png")
                        if attempt == 0: continue
                        return False
            except Exception as e:
                logger.info(f"GreenhouseHandler: Error during resume upload strategy attempt: {e}")
                if attempt == 0: continue
                return False
        return False

    def _extract_questions(self) -> list[dict]:
        logger.info("GreenhouseHandler: DOM PARSER V3 - Extracting questions...")
        questions = []
        ignored_options = 0
        total_options = 0

        # The "USA - Self-Identification Survey" / EEO demographic block
        # (Gender, Race, Veteran Status, Disability Status, etc.) wraps each
        # question in `div.select__container` directly under
        # `div.demographic--container`, skipping the `div.field-wrapper`
        # level every other custom question routes through — so it's
        # invisible to the selectors above unless scoped in explicitly. The
        # demographic-scoped descendant selector only matches inside that
        # block, so it can't create duplicate containers for fields that
        # already match via `div.field-wrapper`.
        selectors = (
            'div.field, div.field-wrapper, fieldset, [role="group"], [role="radiogroup"], [role="listbox"], '
            'div.demographic--container div.select__container'
        )
        containers = self.active_context.locator(selectors).all()

        for container in containers:
            try:
                if not container.is_visible(): continue
                label_loc = container.locator('label, legend').first
                if label_loc.count() == 0: continue

                raw_text = label_loc.inner_text().split('\n')[0].strip()
                if not raw_text: continue

                is_required = "*" in raw_text
                if not is_required:
                    req_inputs = container.locator('[required], [aria-required="true"]')
                    if req_inputs.count() > 0:
                        is_required = True

                clean_label = raw_text.replace("*", "").strip()

                skip_list = ["first name", "last name", "email", "phone", "resume", "cv", "resume/cv", "cover letter", "cover_letter", "country", "attach", "enter manually"]
                if clean_label.lower() in skip_list: continue

                options = []
                widget_type = "unknown"
                placeholder = ""

                radios = container.locator('input[type="radio"]')
                checkboxes = container.locator('input[type="checkbox"]')
                rs_loc = container.locator('div[class*="select__control"], div[class*="-control"]')

                if rs_loc.count() > 0:
                    widget_type = "react_select"
                elif radios.count() > 0 or checkboxes.count() > 0:
                    widget_type = "radio_group" if radios.count() > 0 else "checkbox_group"
                    opts_count = radios.count() + checkboxes.count()
                    total_options += opts_count
                    ignored_options += opts_count
                    all_labels = container.locator('label').all_inner_texts()
                    if len(all_labels) > 1:
                        options = [l.strip() for l in all_labels[1:] if l.strip()]
                elif container.locator('select').count() > 0:
                    widget_type = "native_select"
                    options = [opt.strip() for opt in container.locator('option').all_inner_texts() if opt.strip() and "select" not in opt.lower()]
                    total_options += len(options)
                elif container.locator('textarea').count() > 0:
                    widget_type = "textarea"
                    ph = container.locator('textarea').first.get_attribute("placeholder")
                    if ph: placeholder = ph
                elif container.locator('input[type="text"], input[type="number"], input[type="email"], input[type="tel"]').count() > 0:
                    widget_type = "input"
                    ph = container.locator('input').first.get_attribute("placeholder")
                    if ph: placeholder = ph

                questions.append({
                    "container": container, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                pass

        logger.info(f"Detected Questions | Count: {len(questions)} | Options: {total_options} | Ignored: {ignored_options}")
        return questions

    def _get_submit_button_locator(self):
        return self.active_context.locator('button[type="submit"], #submit_app, input[type="submit"]').first

    def _react_select_current_value(self, container) -> str:
        """Reads the currently selected value of a react-select control.
        Greenhouse has (at least) three variants in the wild: the classic
        single-select exposes its value via a `select__single-value` div;
        multi-select-style widgets (some EEO fields like Gender allow
        multiple values even when only one is meaningfully chosen) render
        each pick as a `select__multi-value` chip instead; and newer
        "remix" design-system fields (class names like
        `remix-css-*-container`) keep the value in the underlying
        `<input>` instead of any value div at all. Checking only one of
        these falsely reports the other two as empty even when a real
        selection was made."""
        val_el = container.locator('div[class*="select__single-value"]')
        if val_el.count() > 0:
            try:
                text = val_el.first.inner_text().strip()
                if text:
                    return text
            except Exception:
                pass
        multi_vals = container.locator('div[class*="select__multi-value__label"], div[class*="-multiValue"]')
        if multi_vals.count() > 0:
            try:
                texts = [t.strip() for t in multi_vals.all_inner_texts() if t.strip()]
                if texts:
                    return ", ".join(texts)
            except Exception:
                pass
        try:
            inp = container.locator('div[class*="select__control"], div[class*="-control"]').locator('input').first
            if inp.count() > 0:
                return (inp.input_value() or "").strip()
        except Exception:
            pass
        return ""

    def _interact_custom_dropdown(self, container, answer: str, interaction: dict) -> bool:
        """Greenhouse's React Select widget — the one non-native dropdown
        across the three ATS this engine currently supports."""
        interaction["Selector Used"] = "div[class*='select__control']"
        rs_loc = container.locator('div[class*="select__control"], div[class*="-control"]')
        rs_loc.first.click(timeout=3000, force=True)

        # Scope the option search to THIS widget's own listbox, not the whole
        # page/frame. A page-wide `div[class*="-option"]` search can match a
        # different react-select's (possibly stale/hidden) option list when
        # several of these widgets exist on one form, silently clicking the
        # wrong field's option instead of this one's.
        input_id = None
        try:
            input_id = rs_loc.first.locator('input').first.get_attribute("id")
        except Exception:
            pass
        if input_id:
            options_loc = self.active_context.locator(f'[id^="react-select-{input_id}-option"]')
        else:
            options_loc = container.locator('div[class*="-option"]')

        try:
            options_loc.first.wait_for(state="visible", timeout=3000)
        except Exception:
            pass

        option_el = options_loc.filter(has_text=answer).first
        if option_el.count() > 0:
            interaction["Interaction Method"] = "click()"
            option_el.click(timeout=3000, force=True)
        else:
            interaction["Interaction Method"] = "partial click()"
            all_opts = options_loc.all()
            for opt in all_opts:
                if answer.lower() in opt.inner_text().lower():
                    opt.click(timeout=3000, force=True)
                    break

        self.page.wait_for_timeout(400)
        val = self._react_select_current_value(container)
        if answer.lower() in val.lower():
            return True

        # Voluntary EEO fields (race, gender identity, etc.) offer an
        # "opt out" option whose exact wording varies per company — "I don't
        # wish to answer", "Decline to Self Identify", "Prefer not to say"
        # all mean the same thing. If our own answer signals a decline
        # intent, match ANY option using one of the common opt-out phrasings
        # instead of requiring the literal string to appear verbatim.
        decline_intent_kw = ["decline", "prefer not", "wish to answer", "self-identify", "self identify"]
        if any(kw in answer.lower() for kw in decline_intent_kw):
            decline_option_kw = ["decline", "wish to answer", "prefer not", "prefer to self-describe", "not disclosed", "rather not"]
            for opt in options_loc.all():
                if any(kw in opt.inner_text().lower() for kw in decline_option_kw):
                    interaction["Interaction Method"] = "decline-synonym click()"
                    opt.click(timeout=3000, force=True)
                    self.page.wait_for_timeout(400)
                    val = self._react_select_current_value(container)
                    if val:
                        return True
                    break

        # Autocomplete fallback (used for things like location fields that
        # query an external places API rather than offering a static option
        # list). A compound query like "Ghaziabad, India" can confuse the
        # places API; searching just the city name alone reliably surfaces
        # the real city as the top (most populous/relevant) suggestion, so
        # search on the first token only and take that top result.
        interaction["Interaction Method"] = "autocomplete search"
        rs_loc.first.click(force=True)
        inp = rs_loc.first.locator('input')
        if inp.count() > 0:
            answer_tokens = [t.strip() for t in re.split(r'[,\s]+', answer) if len(t.strip()) > 1]
            query = answer_tokens[0] if answer_tokens else answer

            self._human_type(inp.first, query, clear_first=True)
            self.page.wait_for_timeout(1500)
            first_suggestion = self.active_context.locator('div[class*="-option"]').first
            if first_suggestion.count() > 0:
                first_suggestion.click(timeout=2000, force=True)
        else:
            rs_loc.first.press('Enter')

        self.page.wait_for_timeout(300)
        val = self._react_select_current_value(container)
        if not val:
            return False
        val_lower = val.lower()
        answer_tokens = [t.strip().lower() for t in re.split(r'[,\s]+', answer) if len(t.strip()) > 1]
        if answer_tokens:
            return all(tok in val_lower for tok in answer_tokens)
        return answer.lower() in val_lower

    def _custom_field_is_empty(self, container, widget_type: str):
        if widget_type != "react_select":
            return None
        val = self._react_select_current_value(container)
        return not val or val == "[]" or val == "Select..."
