from src.system.logger import setup_logger
logger = setup_logger('greenhouse')
import re
import time
import os
from playwright.sync_api import Page
from src.applications.question_engine import QuestionEngine
from src.applications.profile import ProfileManager
from src.applications.question_classifier import QuestionClassifier
from src.system.state import WorkflowState

class GreenhouseHandler:
    def __init__(self, page: Page, job_title: str, company_name: str, location: str, resume_path: str, test_mode: bool = False, execution_dir: str = "", profile_manager=None, rag_client=None, llm_client=None, company_context: str = ""):
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
            job_title=job_title
        )
        self.active_context = self.page
        
    def _calculate_form_confidence(self, context) -> int:
        score = 0
        
        # +30 Resume Upload
        if context.locator('input[type="file"]').count() > 0: score += 30
        elif context.locator('button:has-text("Attach"), button:has-text("Upload"), button:has-text("Browse")').count() > 0: score += 30
        
        # +20 First Name
        if context.locator('label:has-text("First Name"), input[name="first_name"]').count() > 0: score += 20
        
        # +20 Last Name
        if context.locator('label:has-text("Last Name"), input[name="last_name"]').count() > 0: score += 20
        
        # +20 Email
        if context.locator('label:has-text("Email"), input[name="email"]').count() > 0: score += 20
        
        # +15 Phone Number
        if context.locator('label:has-text("Phone"), input[name="phone"]').count() > 0: score += 15
        
        # +30 Submit Application
        if context.locator('button:has-text("Submit Application"), input[type="submit"][value*="Submit"], button#submit_app').count() > 0: score += 30
        
        return score
        
    def _enter_application_flow(self):
        logger.info("GreenhouseHandler: Entering application flow...")
        if not hasattr(self, "telemetry"): self.telemetry = {}
        
        # 1. Check if we are already in flow
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(2000)
        
        # If the form is embedded in an iframe immediately, we might need to check iframes too
        best_score = self._calculate_form_confidence(self.page)
        best_context = self.page
        
        for frame in self.page.frames:
            f_score = self._calculate_form_confidence(frame)
            if f_score > best_score:
                best_score = f_score
                best_context = frame
                
        logger.info(f"  -> Initial Form Confidence Score: {best_score}")
        
        if best_score >= 50:
            logger.info("  -> Application form detected initially. Proceeding.")
            self.active_context = best_context
            return
            
        logger.info("  -> Form not detected. Searching for Apply button...")
        
        apply_texts = ["Apply for this role", "Apply for this job", "Apply now", "Apply", "Continue application"]
        
        target_btn = None
        target_text = ""
        
        for text in apply_texts:
            btn = self.page.locator(f'button:has-text("{text}"), a:has-text("{text}")').first
            if btn.count() > 0 and btn.is_visible() and not btn.is_disabled():
                target_btn = btn
                target_text = text
                break
                
        if not target_btn:
            # Maybe it's not strictly exactly the text, try case-insensitive or partial
            btn = self.page.locator(f'button:text-matches("apply", "i"), a:text-matches("apply", "i")').first
            if btn.count() > 0 and btn.is_visible() and not btn.is_disabled():
                target_btn = btn
                target_text = btn.inner_text().strip()
                
        if not target_btn:
            self.telemetry["form_confidence_score"] = best_score
            raise Exception("APPLICATION_FORM_NOT_DETECTED: No Apply button found and initial score < 50.")
            
        url_before = self.page.url
        logger.info(f"  -> Clicking Apply button: '{target_text}'")
        
        # Handle potential new tab
        try:
            with self.page.context.expect_page(timeout=5000) as new_page_info:
                target_btn.click(timeout=5000)
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            new_page.wait_for_timeout(2000)
            logger.info("  -> Navigation Type: Popup/New Tab")
            self.page = new_page # Switch primary context
            self.active_context = self.page
        except Exception:
            # No new page spawned, it's either redirect, modal, or same-page
            try:
                target_btn.click(timeout=5000)
                self.page.wait_for_timeout(3000)
            except Exception as e:
                logger.info(f"  -> Warning: Click on Apply failed: {e}")
                
            nav_type = "Same Page/Modal"
            if self.page.url != url_before:
                nav_type = "Redirect"
            logger.info(f"  -> Navigation Type: {nav_type}")
            
        url_after = self.page.url
        
        self.telemetry["entry_action_text"] = target_text
        self.telemetry["url_before"] = url_before
        self.telemetry["url_after"] = url_after
        self.telemetry["navigation_type"] = "Popup/New Tab" if 'new_page' in locals() else nav_type
        
        # Verify again
        final_score = self._calculate_form_confidence(self.page)
        for frame in self.page.frames:
            f_score = self._calculate_form_confidence(frame)
            if f_score > final_score:
                final_score = f_score
                
        self.telemetry["form_confidence_score"] = final_score
        logger.info(f"  -> Post-click Form Confidence Score: {final_score}")
        
        if final_score < 50:
            raise Exception("APPLICATION_FORM_NOT_DETECTED: Apply button clicked but form confidence score < 50.")
            
        self.active_context = best_context
        logger.info("  -> Application flow entered successfully.")
        
    def _detect_and_set_iframe(self):
        logger.info("GreenhouseHandler: Scanning for iframes...")
        try:
            self.page.wait_for_timeout(2000) # Give frames a moment to load
            iframes = self.page.frames
            logger.info(f"  -> Found {len(iframes)} frames.")
            for frame in iframes:
                url = frame.url.lower()
                logger.info(f"  -> Frame URL: {url}")
                if "boards.greenhouse.io" in url or "greenhouse.io" in url or "application" in url:
                    logger.info(f"GreenhouseHandler: Detected Greenhouse iframe ({url}). Promoting to active_context.")
                    self.active_context = frame
                    if not hasattr(self, "telemetry"): self.telemetry = {}
                    self.telemetry["iframe_detected"] = True
                    self.telemetry["iframe_url"] = url
                    return
        except Exception as e:
            logger.info(f"  -> Iframe scan error: {e}")
        logger.info("GreenhouseHandler: No matching iframe found. Using main page as active_context.")
        
    def _capture_screenshot(self, name: str):
        if self.execution_dir:
            import os
            os.makedirs(self.execution_dir, exist_ok=True)
            self.page.screenshot(path=os.path.join(self.execution_dir, name))
        
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
                        input_el.fill(val, timeout=3000)
                    
                    self.page.wait_for_timeout(200)
                    if not input_el.input_value():
                        logger.info(f"GreenhouseHandler: Field {key} empty after fill. Retrying...")
                        input_el.fill(val, timeout=3000)
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
                    
        return safe_to_proceed

    def _upload_resume(self) -> bool:
        logger.info(f"GreenhouseHandler: Uploading resume {self.resume_path}...")
        
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}
        self.telemetry["resume_filename"] = os.path.basename(self.resume_path)
        self.telemetry["resume_upload_success"] = False
        
        if not os.path.exists(self.resume_path):
            logger.info(f"Resume Upload Failed: File does not exist at {self.resume_path}")
            return False
            
        # Copy and rename resume for ATS parsing
        import shutil
        safe_company = re.sub(r'[^a-zA-Z0-9]', '', self.company_name)
        safe_title = re.sub(r'[^a-zA-Z0-9]', '', self.job_title)
        if not safe_company: safe_company = "Company"
        if not safe_title: safe_title = "Role"
        
        new_resume_name = f"Resume_{safe_company}_{safe_title}.pdf"
        
        # Determine directory for the new file
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
                # Load adaptive learning strategy
                import json
                strategy_file = "data/upload_strategies.json"
                known_strategy = None
                if os.path.exists(strategy_file):
                    try:
                        with open(strategy_file, "r") as f:
                            strategies = json.load(f)
                            known_strategy = strategies.get(self.company_name)
                    except: pass
                    
                upload_success = False
                
                strategies = [
                    {"name": "A", "desc": "input[type='file']", "loc": 'input[type="file"]'},
                    {"name": "B", "desc": "button (Attach/Upload/Browse)", "loc": 'button:has-text("Attach"), button:has-text("Upload"), button:has-text("Browse")'},
                    {"name": "C", "desc": "label associated with upload", "loc": 'label:has-text("Resume"), label:has-text("CV")'},
                    {"name": "E", "desc": "aria-label search", "loc": '[aria-label*="Upload"], [aria-label*="Resume"], [aria-label*="CV"]'}
                ]
                
                if known_strategy:
                    # Move known strategy to front
                    strategies = [s for s in strategies if s["name"] == known_strategy] + [s for s in strategies if s["name"] != known_strategy]
                    
                for strat in strategies:
                    logger.info(f"  -> Trying Strategy {strat['name']}: {strat['desc']}")
                    loc = self.active_context.locator(strat['loc']).first
                    if loc.count() > 0:
                        try:
                            if strat['name'] == 'A':
                                # Input file can just take set_input_files
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
                                # Save strategy
                                try:
                                    s_data = {}
                                    if os.path.exists(strategy_file):
                                        with open(strategy_file, "r") as f:
                                            s_data = json.load(f)
                                    s_data[self.company_name] = strat['name']
                                    with open(strategy_file, "w") as f:
                                        json.dump(s_data, f)
                                except: pass
                                break
                        except Exception as e:
                            logger.info(f"  -> Strategy {strat['name']} failed: {e}")
                            
                if not upload_success:
                    logger.info(f"  -> All upload strategies failed. (Attempt {attempt+1})")
                    if attempt == 0: continue
                    return False
                
                resume_name_only = os.path.splitext(new_resume_name)[0]
                
                # Check for error banners
                error_banners = self.active_context.locator('.error-message, .validation-error, [role="alert"]').all_inner_texts()
                if any("resume" in err.lower() or "upload" in err.lower() or "file" in err.lower() for err in error_banners):
                    logger.info(f"  -> Upload Verified: False (Error banner detected). (Attempt {attempt+1})")
                    if attempt == 0: continue
                    return False
                
                try:
                    # Wait for either the full name or the name without extension
                    self.active_context.wait_for_selector(f"text={resume_name_only}", timeout=8000)
                    logger.info(f"  -> Upload Verified: True")
                    self.telemetry["resume_upload_success"] = True
                    self.telemetry["resume_upload_time"] = datetime.now().isoformat()
                    self.telemetry["filled_fields"]["Resume"] = True
                    return True
                except Exception:
                    try:
                        # Fallback: check for 'Remove' link which appears after upload
                        self.active_context.wait_for_selector('button:has-text("Remove"), a:has-text("Remove")', timeout=4000)
                        logger.info(f"  -> Upload Verified: True (via Remove button)")
                        self.telemetry["resume_upload_success"] = True
                        self.telemetry["resume_upload_time"] = datetime.now().isoformat()
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
        
        selectors = 'div.field, div.field-wrapper, fieldset, [role="group"], [role="radiogroup"], [role="listbox"]'
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
                
                skip_list = ["first name", "last name", "email", "phone", "resume", "cv", "resume/cv", "country", "attach", "enter manually"]
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
                    "container": container,
                    "question": clean_label,
                    "raw_label": raw_text,
                    "is_required": is_required,
                    "widget_type": widget_type,
                    "options": options,
                    "placeholder": placeholder
                })
            except Exception as e:
                pass
                
        logger.info("\n==================================================")
        logger.info("Detected Questions")
        logger.info(f"Question Count: {len(questions)}")
        logger.info(f"Option Count: {total_options}")
        logger.info(f"Ignored Option Labels: {ignored_options}")
        logger.info("==================================================\n")
        
        return questions

    def _process_custom_fields(self, telemetry: dict) -> bool:
        """
        Iterates over custom fields. Returns True if all successfully answered and safe to auto-submit.
        """
        logger.info("GreenhouseHandler: Processing custom fields...")
        safe_to_submit = True
        
        if 'interaction_log' not in telemetry:
            telemetry['interaction_log'] = []
            
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
            if widget_type in ["react_select", "native_select", "radio_group"]: field_type = "dropdown"
            elif widget_type == "checkbox_group": field_type = "multiselect"
            elif widget_type == "textarea": field_type = "textarea"
            
            dom_meta = {
                "css_selector": "",
                "input_tag": widget_type,
                "visible": True,
                "disabled": False,
                "current_value": "",
                "widget_type": widget_type
            }
            
            # Dynamic extraction for React Select options before answering
            if widget_type == "react_select" and not options:
                try:
                    rs_loc = container.locator('div[class*="select__control"], div[class*="-control"]')
                    if rs_loc.count() > 0:
                        rs_loc.first.click(timeout=1000, force=True)
                        self.page.wait_for_timeout(300)
                        opts = self.active_context.locator('div[class*="-option"]').all_inner_texts()
                        options = [o.strip() for o in opts if o.strip()]
                except Exception as e:
                    logger.info(f"Failed to pre-load react_select options: {e}")
                    
            # 1.6A: Classify the question before answering
            classification = QuestionClassifier.classify(clean_label, widget_type)
            if classification == "ESCALATE":
                logger.info(f"GreenhouseHandler: Escalating complex question '{clean_label}' -> REVIEW_REQUIRED")
                safe_to_submit = False
                continue

            answer = self.engine.answer(
                question=clean_label,
                field_type=field_type,
                placeholder=placeholder,
                options=options,
                label_text=label_text,
                required=is_required,
                dom_meta=dom_meta
            )
            
            if answer == "NORMALIZATION_FAILED":
                safe_to_submit = False
                continue
                
            conf = dom_meta.get("confidence", 100)
            if conf < 70:
                logger.info(f"Validation Error: Answer for '{clean_label}' has confidence {conf} < 70. Triggering REVIEW_REQUIRED.")
                if "missing_fields" not in telemetry:
                    telemetry["missing_fields"] = []
                telemetry["missing_fields"].append({
                    "type": "PROFILE_MISSING_FIELD",
                    "question": clean_label,
                    "confidence": conf
                })
                safe_to_submit = False
                continue
            elif conf < 90:
                logger.info(f"Warning: Answer for '{clean_label}' has confidence {conf} (70-89). Proceeding with warning.")
                
            if answer == "REVIEW_REQUIRED":
                logger.info(f"Validation Error: Answer for '{clean_label}' resolved to REVIEW_REQUIRED. Aborting interaction.")
                if "missing_fields" not in telemetry:
                    telemetry["missing_fields"] = []
                telemetry["missing_fields"].append({
                    "type": "PROFILE_MISSING_FIELD",
                    "question": clean_label,
                    "reason": "Explicit REVIEW_REQUIRED from resolver"
                })
                safe_to_submit = False
                continue
                
            if is_required and not answer:
                safe_to_submit = False
                continue
                
            if not answer:
                continue
                
            # Telemetry counting
            telemetry["question_count"] += 1
            last_log = self.engine.audit_log[-1] if self.engine.audit_log else {}
            if last_log.get("source") == "LLM":
                telemetry["llm_question_count"] += 1
            else:
                telemetry["profile_question_count"] += 1

            interaction = {
                "Question": clean_label,
                "Expected Value": answer,
                "Selector Used": "",
                "Interaction Method": "",
                "Verification Result": False
            }

            try:
                selection_success = False
                
                if widget_type == "react_select":
                    interaction["Selector Used"] = "div[class*='select__control']"
                    rs_loc = container.locator('div[class*="select__control"], div[class*="-control"]')
                    rs_loc.first.click(timeout=1000, force=True)
                    self.page.wait_for_timeout(300)
                    
                    option_el = self.active_context.locator(f'div[class*="-option"]:has-text("{answer}")').first
                    if option_el.count() > 0:
                        interaction["Interaction Method"] = "click()"
                        option_el.click(timeout=1000, force=True)
                    else:
                        # Try partial match
                        interaction["Interaction Method"] = "partial click()"
                        all_opts = self.active_context.locator('div[class*="-option"]').all()
                        for opt in all_opts:
                            if answer.lower() in opt.inner_text().lower():
                                opt.click(timeout=1000, force=True)
                                break
                    
                    # Verification
                    self.page.wait_for_timeout(300)
                    val_el = container.locator('div[class*="select__single-value"]')
                    val = val_el.inner_text().strip() if val_el.count() > 0 else ""
                    if answer.lower() in val.lower():
                        selection_success = True
                    else:
                        # Fallback to press Enter
                        interaction["Interaction Method"] = "press('Enter')"
                        rs_loc.first.click(force=True)
                        inp = rs_loc.first.locator('input')
                        if inp.count() > 0:
                            inp.first.fill(answer)
                            self.page.wait_for_timeout(2000) # Wait for autocomplete to populate
                            inp.first.press('ArrowDown')
                            self.page.wait_for_timeout(500)
                            inp.first.press('Enter')
                        else:
                            rs_loc.first.press('Enter')
                            
                        self.page.wait_for_timeout(300)
                        val = val_el.inner_text().strip() if val_el.count() > 0 else ""
                        selection_success = answer.lower() in val.lower() or ('location' in clean_label.lower() and val != '')
                        
                elif widget_type == "native_select":
                    interaction["Selector Used"] = "select"
                    interaction["Interaction Method"] = "select_option"
                    select_loc = container.locator('select')
                    select_loc.first.select_option(label=answer)
                    select_loc.first.evaluate("el => $(el).trigger('change')")
                    selection_success = True
                    
                elif widget_type == "textarea":
                    interaction["Selector Used"] = "textarea"
                    interaction["Interaction Method"] = "fill()"
                    ta = container.locator('textarea').first
                    ta.fill(answer)
                    selection_success = (ta.input_value() == answer)
                    
                elif widget_type == "input":
                    interaction["Selector Used"] = "input:not([type='hidden'])"
                    inp = container.locator('input:not([type="hidden"])').first
                    if inp.count() > 0:
                        interaction["Interaction Method"] = "fill()"
                        
                        # Handle split OTP fields (e.g. Stripe)
                        if inp.get_attribute("maxlength") == "1" and len(answer) > 1:
                            all_inps = container.locator('input:not([type="hidden"])')
                            for i in range(min(all_inps.count(), len(answer))):
                                all_inps.nth(i).fill(answer[i])
                                self.page.wait_for_timeout(50)
                            val = answer
                            selection_success = True
                        else:
                            inp.fill(answer)
                            self.page.wait_for_timeout(200)
                            val = inp.input_value()
                            if val != answer:
                                interaction["Interaction Method"] = "type()"
                                inp.fill("")
                                inp.type(answer, delay=10)
                                val = inp.input_value()
                            selection_success = (val == answer)
                    else:
                        selection_success = False
                    
                elif widget_type in ["radio_group", "checkbox_group"]:
                    interaction["Selector Used"] = "label containing answer"
                    interaction["Interaction Method"] = "check()"
                    found = False
                    
                    # Handle single boolean checkboxes (consent/policy)
                    if widget_type == "checkbox_group" and answer in ["True", "Yes"]:
                        chk = container.locator('input[type="checkbox"]').first
                        if chk.count() > 0:
                            chk.check(force=True)
                            found = True
                    
                    if not found:
                        labels = container.locator('label').all()
                        for lbl in labels:
                            if answer.lower() in lbl.inner_text().lower():
                                inp = lbl.locator('input')
                                if inp.count() == 0:
                                    inp = container.locator(f'input[id="{lbl.get_attribute("for")}"]')
                                if inp.count() > 0:
                                    inp.first.check(force=True)
                                    found = True
                                    break
                    selection_success = found

                interaction["Verification Result"] = selection_success
                if not selection_success:
                    safe_to_submit = False
                    
            except Exception as e:
                interaction["Verification Result"] = False
                interaction["Error"] = str(e)
                safe_to_submit = False
                
            telemetry['interaction_log'].append(interaction)
                
        return safe_to_submit

    def _pre_submit_audit(self) -> bool:
        """Fix 4: Scan all required fields for empty or invalid values."""
        logger.info("GreenhouseHandler: Running Pre-Submit Audit...")
        safe = True
        missing_count = 0
        
        questions = self._extract_questions()
        for q in questions:
            if not q["is_required"]: continue
            
            container = q["container"]
            label_text = q["question"]
            widget_type = q["widget_type"]
            
            # AUDIT EXCEPTION: Ignore OTP Fields
            label_lower = label_text.lower()
            if "security code" in label_lower or "verification code" in label_lower or "otp" in label_lower or "enter the 8-character code" in label_lower:
                continue
            
            try:
                if widget_type == "input":
                    inputs = container.locator('input:not([type="hidden"])')
                    for i in range(inputs.count()):
                        el = inputs.nth(i)
                        if el.is_visible() and not el.input_value():
                            logger.info(f"Pre-Submit Audit Failed: Empty required input near '{label_text}'")
                            safe = False
                            missing_count += 1
                elif widget_type == "textarea":
                    textareas = container.locator('textarea')
                    for i in range(textareas.count()):
                        el = textareas.nth(i)
                        if el.is_visible() and not el.input_value():
                            logger.info(f"Pre-Submit Audit Failed: Empty required textarea near '{label_text}'")
                            safe = False
                            missing_count += 1
                elif widget_type == "native_select":
                    selects = container.locator('select')
                    for i in range(selects.count()):
                        el = selects.nth(i)
                        if el.is_visible() and not el.input_value():
                            logger.info(f"Pre-Submit Audit Failed: Empty required select near '{label_text}'")
                            safe = False
                            missing_count += 1
                elif widget_type == "react_select":
                    rs = container.locator('div[class*="select__single-value"]')
                    for i in range(rs.count()):
                        el = rs.nth(i)
                        if el.is_visible():
                            val = el.inner_text()
                            if not val or val == "[]" or val == "Select...":
                                logger.info(f"Pre-Submit Audit Failed: Invalid React Select value '{val}' near '{label_text}'")
                                safe = False
                                missing_count += 1
                elif widget_type in ["radio_group", "checkbox_group"]:
                    inputs = container.locator('input')
                    checked = False
                    for i in range(inputs.count()):
                        if inputs.nth(i).is_checked():
                            checked = True
                            break
                    if not checked:
                        logger.info(f"Pre-Submit Audit Failed: No option selected near '{label_text}'")
                        safe = False
                        missing_count += 1
            except Exception as e:
                logger.info(f"Pre-Submit Audit Warning near label: {e}")
                
        if missing_count > 0:
            logger.info(f"GreenhouseHandler: ABORTING SUBMISSION. Detected {missing_count} empty required fields!")
            return False
            
        return safe

    def _check_for_otp(self) -> bool:
        """Checks if the OTP verification screen is visible using robust signals."""
        try:
            ctx = self.active_context
            # Signal 1: Explicit IDs or fieldsets
            if ctx.locator('fieldset#email-verification, input[id^="security-input-"]').count() > 0:
                return True
            # Signal 2: Standard text prompts
            if ctx.locator('text="Verify Email", text="Enter Code", text="One-Time Password", text="OTP", text="Verification Code"').first.is_visible(timeout=1000):
                return True
            # Signal 3: Multiple single-char inputs near each other (split OTP boxes)
            # Find a container with exactly 6 or 8 max-length 1 inputs
            inputs = ctx.locator('input[maxlength="1"]').all()
            if len(inputs) in [6, 8]:
                return True
                
            return False
        except:
            return False

    def _post_otp_analysis(self) -> dict:
        """Dumps forensic state immediately after an OTP submission."""
        analysis = {
            "current_url": self.page.url,
            "page_title": self.page.title(),
            "visible_headers": [],
            "validation_errors": [],
            "required_fields_remaining": 0
        }
        try:
            for h in self.active_context.locator('h1, h2, h3').all():
                if h.is_visible():
                    analysis["visible_headers"].append(h.inner_text().strip())
                    
            for err in self.active_context.locator('.error-message, .field_with_errors').all():
                if err.is_visible():
                    analysis["validation_errors"].append(err.inner_text().strip())
                    
            # Check remaining inputs roughly
            inputs = self.active_context.locator('input[aria-required="true"], select[aria-required="true"], textarea[aria-required="true"]').all()
            for inp in inputs:
                if inp.is_visible() and not inp.input_value():
                    analysis["required_fields_remaining"] += 1
                    
        except Exception as e:
            analysis["error"] = str(e)
            
        import json
        import os
        if self.execution_dir:
            with open(os.path.join(self.execution_dir, "otp_forensics.json"), "w") as f:
                json.dump(analysis, f, indent=4)
        return analysis

    def _handle_otp(self, telemetry: dict) -> str:
        """Handles the OTP retrieval and submission flow with exponential backoff."""
        from src.applications.otp_retriever import retrieve_greenhouse_otp
        from datetime import datetime, timezone, timedelta
        import time
        
        self._capture_screenshot("02_otp_page.png")
        logger.info("GreenhouseHandler: Entering OTP_RETRIEVING state.")
        telemetry['otp_detected'] = True
        
        start_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        code = None
        cumulative_wait = 0
        
        retries = [10, 20, 40]
        for delay in retries:
            logger.info(f"GreenhouseHandler: Fetching OTP... (Wait: {delay}s)")
            self.page.wait_for_timeout(delay * 1000)
            cumulative_wait += delay
            result = retrieve_greenhouse_otp(start_time)
            
            telemetry['otp_forensics_v2'] = result
            telemetry['otp_forensics_v2']['waited_seconds'] = cumulative_wait
            
            if result.get("code"):
                code = result["code"]
                break
                
        if not code:
            logger.info("GreenhouseHandler: OTP Retrieval Failed after max retries.")
            telemetry['otp_received'] = False
            return WorkflowState.OTP_REQUIRED.name
            
        telemetry['otp_received'] = True
        logger.info(f"GreenhouseHandler: OTP Retrieved -> {code}. Entering OTP_SUBMITTED state.")
        
        # Fill the OTP inputs
        try:
            inputs = self.active_context.locator('input:not([type="hidden"])').all()
            # Find the split inputs
            split_inputs = [inp for inp in inputs if inp.get_attribute('maxlength') == "1"]
            if len(split_inputs) == len(code):
                for i in range(len(code)):
                    split_inputs[i].fill(code[i])
                    self.page.wait_for_timeout(50)
            else:
                # Try to find a single input labeled for OTP
                for inp in inputs:
                    if inp.is_visible():
                        inp.fill(code)
                        break
            
            telemetry['otp_submitted'] = True
            self._capture_screenshot("03_after_otp_filled.png")
            logger.info("GreenhouseHandler: OTP Filled. Awaiting submit...")
            return "OTP_SUBMITTED"
        except Exception as e:
            logger.info(f"GreenhouseHandler: Error filling OTP: {e}")
            return WorkflowState.REVIEW_REQUIRED.name

    def _diagnose_submission_blocker(self) -> dict:
        diagnosis = {
            "resume_issue": [],
            "missing_fields": [],
            "validation_errors": [],
            "otp_detected": self._check_for_otp()
        }
        
        if self.active_context.locator('button:has-text("Attach")').is_visible():
            diagnosis["resume_issue"].append("Resume missing or upload failed")
        
        errors = self.active_context.locator('.error-message, .field_with_errors, [aria-invalid="true"]').all()
        for e in errors:
            if e.is_visible():
                text = e.inner_text().strip()
                if text: diagnosis["validation_errors"].append(text)
                
        questions = self._extract_questions()
        for q in questions:
            if not q["is_required"]: continue
            
            container = q["container"]
            label_text = q["question"]
            widget_type = q["widget_type"]
            is_empty = True
            
            try:
                if widget_type == "input":
                    inputs = container.locator('input:not([type="hidden"])').all()
                    for inp in inputs:
                        if inp.is_visible() and inp.input_value().strip(): is_empty = False
                elif widget_type == "textarea":
                    for inp in container.locator('textarea').all():
                        if inp.is_visible() and inp.input_value().strip(): is_empty = False
                elif widget_type == "native_select":
                    for inp in container.locator('select').all():
                        if inp.is_visible() and inp.input_value().strip(): is_empty = False
                elif widget_type == "react_select":
                    rs = container.locator('div[class*="select__single-value"]')
                    if rs.is_visible():
                        val = rs.inner_text().strip()
                        if val and val != "[]" and val != "Select...": is_empty = False
                elif widget_type in ["radio_group", "checkbox_group"]:
                    inputs = container.locator('input')
                    for i in range(inputs.count()):
                        if inputs.nth(i).is_checked():
                            is_empty = False
                            break
                            
                if is_empty:
                    diagnosis["missing_fields"].append(label_text)
            except: pass
                    
        return diagnosis

    def _attempt_repair(self, diagnosis: dict) -> bool:
        """Attempts to deterministically repair missing fields or OTPs."""
        repaired_any = False
        
        # 1. Handle OTP
        if diagnosis.get("otp_detected"):
            logger.info("GreenhouseHandler: OTP Challenge Detected. Launching OTP Retriever...")
            
            # Log this learning action
            if not hasattr(self, "learning_log"):
                self.learning_log = []
                
            from src.applications.otp_retriever import retrieve_greenhouse_otp
            import datetime
            start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)
            
            otp_code = retrieve_greenhouse_otp(start_time)
            
            if otp_code:
                try:
                    logger.info("OTP Detected")
                    logger.info("OTP Retrieved")
                    logger.info(f"OTP Length: {len(otp_code)}")
                    
                    # 1. Look for split inputs (security-input-0, security-input-1, etc.)
                    security_inputs = self.active_context.locator('input[id^="security-input-"]')
                    boxes_filled = 0
                    
                    if security_inputs.count() > 0:
                        for i in range(min(security_inputs.count(), len(otp_code))):
                            security_inputs.nth(i).fill(otp_code[i])
                            self.page.wait_for_timeout(100)
                            boxes_filled += 1
                    else:
                        # Fallback for single input box
                        otp_input = self.active_context.locator('input[type="text"], input[name*="code"], input[name*="otp"]').first
                        if otp_input.is_visible():
                            otp_input.fill(otp_code)
                            boxes_filled += 1
                            
                    logger.info(f"Boxes Filled: {boxes_filled}")
                            
                    if boxes_filled > 0:
                        verify_btn = self.active_context.locator('button:has-text("Verify"), button:has-text("Submit")').first
                        if verify_btn.is_visible():
                            verify_btn.click(timeout=5000)
                            logger.info("Verification Result: Submitted")
                            
                            self.learning_log.append({
                                "problem": "OTP Verification Required",
                                "repair": "Retrieve OTP from Gmail",
                                "result": "Success"
                            })
                            
                            if not hasattr(self, "telemetry"):
                                self.telemetry = {}
                            self.telemetry["otp_detected"] = True
                            self.telemetry["otp_retrieved"] = otp_code
                            self.telemetry["otp_success"] = True
                            
                            return True
                except Exception as e:
                    logger.info(f"Verification Result: Failed to fill OTP: {e}")
                    
            logger.info("OTP_REQUIRED")
            logger.info("Reason: OTP_EMAIL_NOT_FOUND")
            self.learning_log.append({
                "problem": "OTP Verification Required",
                "repair": "Retrieve OTP from Gmail",
                "result": "Failed"
            })
            return False

        if not diagnosis.get("missing_fields"):
            return False
            
        logger.info("GreenhouseHandler: Attempting Auto-Repair for missing fields...")
        
        repair_map = {
            "gender": self.profile.get_field("gender") or "Male",
            "graduation": str(self.profile.get_field("graduation_year") or "2026"),
            "current organization": self.profile.get_field("current_organization") or "IIT Roorkee",
            "notice period": str(self.profile.get_field("notice_period_days") or "15"),
            "linkedin": self.profile.get_field("linkedin") or "https://linkedin.com/in/yash-kherwal-944497254/"
        }
        
        questions = self._extract_questions()
        for q in questions:
            clean_label = q["question"]
            container = q["container"]
            widget_type = q["widget_type"]
            
            if clean_label in diagnosis["missing_fields"]:
                fix_value = None
                for key, val in repair_map.items():
                    if key.lower() in clean_label.lower():
                        fix_value = val
                        break
                
                if fix_value:
                    logger.info(f"  -> Auto-Repairing '{clean_label}' with '{fix_value}'")
                    
                    try:
                        if widget_type == "react_select":
                            rs = container.locator('div[class*="select__control"], div[class*="-control"]')
                            if rs.is_visible():
                                rs.click(timeout=2000, force=True)
                                self.page.wait_for_timeout(300)
                                options = self.active_context.locator('div[class*="-option"]')
                                for i in range(options.count()):
                                    opt = options.nth(i)
                                    if fix_value.lower() in opt.inner_text().lower():
                                        opt.click(timeout=1000)
                                        repaired_any = True
                                        break
                                else:
                                    rs.click(timeout=1000, force=True) # close if no match
                        elif widget_type in ["input", "textarea"]:
                            inputs = container.locator('input:not([type="hidden"]), textarea')
                            if inputs.is_visible():
                                inputs.fill(fix_value)
                                repaired_any = True
                        elif widget_type == "native_select":
                            selects = container.locator('select')
                            if selects.is_visible():
                                selects.select_option(label=fix_value)
                                repaired_any = True
                    except: pass

        return repaired_any

    def execute(self) -> dict:
        """
        Executes the Greenhouse application workflow.
        Returns a dict with status and audit log.
        """
        telemetry = {
            "question_count": 0,
            "llm_question_count": 0,
            "profile_question_count": 0,
            "filled_fields": {
                "Resume": False,
                "Email": False,
                "Phone": False,
                "LinkedIn": False,
                "Questions": False,
                "Attachments": False
            }
        }
        if hasattr(self, "telemetry"):
            # Merge nested dicts carefully
            filled_fields = telemetry["filled_fields"]
            if "filled_fields" in self.telemetry:
                filled_fields.update(self.telemetry["filled_fields"])
            telemetry.update(self.telemetry)
            telemetry["filled_fields"] = filled_fields
            
        self.telemetry = telemetry
        
        try:
            self._enter_application_flow()
            self._detect_and_set_iframe()
            
            from src.applications.verifier import SubmissionVerifier
            self._capture_screenshot("01_page_loaded.png")
            
            # Use the new robust method
            standard_fields_safe = self._fill_and_verify_standard_fields()
            if not standard_fields_safe:
                logger.info("GreenhouseHandler: Standard field validation failed. Safety Pause.")
                self._capture_screenshot("05_pre_submit.png")
                return {"status": WorkflowState.REVIEW_REQUIRED.name, "audit_log": self.engine.audit_log, "telemetry": telemetry}
                
            self._capture_screenshot("03_profile_completed.png")
            upload_success = self._upload_resume()
            if not upload_success:
                logger.info("GreenhouseHandler: Resume upload failed after retries. Aborting.")
                self._capture_screenshot("03b_resume_upload_failed.png")
                return {"status": WorkflowState.REVIEW_REQUIRED.name, "audit_log": self.engine.audit_log, "telemetry": telemetry}
                
            self._capture_screenshot("02_resume_uploaded.png")
            
            result_status = WorkflowState.FAILED.name
            
            # Main Application Loop (Handles both retries and multi-step pages)
            cycles = 0
            while cycles < 10:
                cycles += 1
                attempt = cycles - 1
                logger.info(f"GreenhouseHandler: Starting cycle {cycles}/10...")
                
                safe_to_submit = self._process_custom_fields(telemetry)
                self._capture_screenshot(f"04_questions_completed_attempt_{attempt}.png")
                
                # Pre-submit audit
                if safe_to_submit:
                    safe_to_submit = self._pre_submit_audit()
                
                if safe_to_submit:
                    logger.info(f"GreenhouseHandler: All checks passed. AUTO-SUBMITTING (Attempt {attempt+1}).")
                    if self.test_mode:
                        logger.info("GreenhouseHandler: TEST MODE ACTIVE. Skipping final submit.")
                        self._capture_screenshot("05_pre_submit.png")
                        result_status = WorkflowState.COMPLETED.name
                        # Mock proof for test mode
                        telemetry["submission_proof"] = {
                            "url": self.page.url,
                            "title": self.page.title(),
                            "success_text": "TEST MODE SUCCESS",
                            "screenshot": "executions/05_pre_submit.png"
                        }
                        break
                    else:
                        # MULTI-STEP CHECK
                        next_btn_texts = ["Continue", "Next", "Review Application", "Proceed"]
                        next_btn = None
                        for text in next_btn_texts:
                            btn = self.active_context.locator(f'button:has-text("{text}"):not([type="submit"]), a:has-text("{text}")').first
                            if btn.count() > 0 and btn.is_visible() and not btn.is_disabled():
                                next_btn = btn
                                break
                                
                        if next_btn:
                            logger.info("GreenhouseHandler: ➡️ Multi-Step Form Detected. Clicking 'Next'...")
                            telemetry["MULTI_STEP_DETECTED"] = True
                            telemetry["step_number"] = telemetry.get("step_number", 1) + 1
                            next_btn.click(timeout=10000)
                            self.page.wait_for_timeout(4000)
                            continue # Process new page fields
                            
                        # Standard Submit
                        submit_btn = self.active_context.locator('button[type="submit"], #submit_app, input[type="submit"]').first
                        
                        # STEP 1: FAST SUBMIT CHECK
                        is_disabled = False
                        try:
                            is_disabled = submit_btn.is_disabled() or submit_btn.get_attribute('aria-disabled') == 'true'
                        except:
                            pass
                            
                        # PRE-SUBMIT OTP CHECK (OTP may appear and disable the submit button)
                        if self._check_for_otp():
                            logger.info("GreenhouseHandler: Verification -> OTP_REQUIRED (Detected before click)")
                            otp_status = self._handle_otp(telemetry)
                            if otp_status == "OTP_SUBMITTED":
                                submit_btn = self.active_context.locator('button[type="submit"], #submit_app').first
                                is_disabled = False
                            else:
                                result_status = otp_status
                                break
                                
                        if is_disabled:
                            logger.info("GreenhouseHandler: 🚫 Submit button is DISABLED. Initiating Diagnosis...")
                            diagnosis = self._diagnose_submission_blocker()
                            import json
                            diag_json = json.dumps(diagnosis)
                            logger.info(f"GreenhouseHandler Diagnosis: {diag_json}")
                            
                            telemetry["diagnosis_json"] = diag_json
                            telemetry["repair_attempts"] = telemetry.get("repair_attempts", 0) + 1
                            
                            repaired = self._attempt_repair(diagnosis)
                            if repaired:
                                logger.info("GreenhouseHandler: Auto-Repair applied. Retrying...")
                                continue # Loop back to submit again
                            else:
                                logger.info("GreenhouseHandler: Auto-Repair failed or no deterministic fix available.")
                                result_status = WorkflowState.REVIEW_REQUIRED.name
                                break
                        
                        # Actual click if enabled
                        try:
                            self._capture_screenshot("01_before_submit.png")
                            telemetry['submit_clicked'] = True
                            submit_btn.click(timeout=10000)
                            logger.info("GreenhouseHandler: Submit button clicked. Waiting 3s for processing...")
                            self.page.wait_for_timeout(3000)
                            if telemetry.get('otp_submitted'):
                                self._capture_screenshot("04_after_otp_submit.png")
                                self._post_otp_analysis()
                        except Exception as click_err:
                            logger.info(f"GreenhouseHandler: Submit click failed: {click_err}")
                            result_status = WorkflowState.FAILED.name
                            break
                        
                        # PRIORITY EVALUATION
                        # 1. Success
                        verification = SubmissionVerifier.verify(self.page, "GREENHOUSE", active_context=self.active_context)
                        telemetry["submission_proof"] = verification["proof"]
                        
                        if verification['status'] == "SUBMITTED_CONFIRMED":
                            logger.info(f"GreenhouseHandler: Verification -> SUCCESS (Confidence: {verification['confidence']}%)")
                            self._capture_screenshot("06_post_submit.png")
                            if self.execution_dir:
                                verification["proof"]["screenshot"] = os.path.join(self.execution_dir, "06_post_submit.png")
                            telemetry["submission_proof"] = verification["proof"]
                            if telemetry.get('otp_submitted'):
                                telemetry['otp_verified'] = True
                            result_status = WorkflowState.COMPLETED.name
                            break
                            
                        # 2. OTP Challenge
                        if self._check_for_otp():
                            logger.info("GreenhouseHandler: Verification -> OTP_REQUIRED")
                            otp_status = self._handle_otp(telemetry)
                            if otp_status == "OTP_SUBMITTED":
                                continue # Loop back to click submit for the OTP
                            else:
                                result_status = otp_status
                                break
                                
                        # 3. Validation Error
                        if verification['status'] == "FAILED_RECOVERABLE" or verification['proof'].get('failure_signals_found', 0) > 0:
                            if telemetry.get('submit_clicked'):
                                logger.info(f"GreenhouseHandler: Verification -> VALIDATION_ERROR. Rule 1 Enforced: NEVER RESUBMIT. Aborting.")
                                self._capture_screenshot(f"05_post_submit_failure_{attempt}.png")
                                result_status = WorkflowState.REVIEW_REQUIRED.name
                                break
                            else:
                                logger.info(f"GreenhouseHandler: Verification -> VALIDATION_ERROR. Retrying...")
                                self._capture_screenshot(f"05_post_submit_failure_{attempt}.png")
                                continue
                            
                        # 4. Generic Failure
                        logger.info(f"GreenhouseHandler: Verification -> {verification['status']} detected: {verification['proof'].get('error_text')}")
                        self._capture_screenshot(f"05_post_submit_failure_{attempt}.png")
                        result_status = WorkflowState.REVIEW_REQUIRED.name
                        break
                else:
                    logger.info("GreenhouseHandler: Safety rules triggered. Moving to REVIEW_REQUIRED.")
                    self._capture_screenshot("05_pre_submit.png")
                    result_status = WorkflowState.REVIEW_REQUIRED.name
                    break
            else:
                # Loop exhausted without breaking
                logger.info("GreenhouseHandler: Maximum retry attempts reached. Moving to REVIEW_REQUIRED.")
                self._capture_screenshot("05_post_submit_failure_final.png")
                result_status = WorkflowState.REVIEW_REQUIRED.name
                
            self._capture_screenshot("05_final_page.png")
            
            if hasattr(self, "learning_log"):
                telemetry["learning_log"] = self.learning_log
                
            return {
                "status": result_status,
                "audit_log": self.engine.audit_log,
                "telemetry": telemetry
            }
            
        except Exception as e:
            logger.info(f"GreenhouseHandler Execution Error: {e}")
            if hasattr(self, "learning_log"):
                telemetry["learning_log"] = self.learning_log
            return {
                "status": WorkflowState.FAILED.name,
                "error": str(e),
                "audit_log": self.engine.audit_log,
                "telemetry": telemetry
            }
