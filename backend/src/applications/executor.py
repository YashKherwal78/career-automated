from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('executor')
import re
import sqlite3
import datetime
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from src.config.config import Config
from src.applications.profile import ProfileManager

class ATSDetector:
    @staticmethod
    def detect(url: str) -> str:
        domain = urlparse(url).netloc.lower()
        if "greenhouse.io" in domain or "gh_jid=" in url:
            return "GREENHOUSE"
        if "lever.co" in domain:
            return "LEVER"
        if "ashbyhq.com" in domain:
            return "ASHBY"
        if "workable.com" in domain:
            return "WORKABLE"
        if "smartrecruiters.com" in domain:
            return "SMARTRECRUITERS"
        if "myworkdayjobs.com" in domain:
            return "WORKDAY"
        return "UNKNOWN"

class ApplicationExecutor:
    def __init__(self, job_id: int, url: str, resume_path: str, profile_type: str = "AI_PROFILE", job_title: str = "Unknown", company_name: str = "Unknown", location: str = "Unknown", test_mode: bool = False, profile_manager=None, rag_client=None, llm_client=None, company_context: str = ""):
        self.job_id = job_id
        self.url = url
        self.resume_path = resume_path
        self.profile_type = profile_type
        self.job_title = job_title
        self.company_name = company_name
        self.location = location
        self.test_mode = test_mode
        self.execution_dir = f"data/executions/{job_id}"
        self.platform = ATSDetector.detect(url)
        self.profile = profile_manager if profile_manager else ProfileManager(profile_type)
        self.rag_client = rag_client
        self.llm_client = llm_client
        self.company_context = company_context
        self.conn = get_connection()
        self.conn.row_factory = sqlite3.Row
        self.audit_log = []
        self.telemetry = {
            "question_count": 0,
            "llm_question_count": 0,
            "profile_question_count": 0
        }
        
    def log_execution(self, status: str, error_reason: str = ""):
        cursor = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        
        # Check if exists
        cursor.execute("SELECT id FROM application_executions WHERE job_id = ?", (self.job_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE application_executions 
                SET status = ?, end_time = ?, error_reason = ?,
                    resume_used = ?, profile_used = ?,
                    question_count = ?, llm_question_count = ?, profile_question_count = ?
                WHERE job_id = ?
            """, (status, now, error_reason, self.resume_path, self.profile_type,
                  self.telemetry.get("question_count", 0), self.telemetry.get("llm_question_count", 0), self.telemetry.get("profile_question_count", 0),
                  self.job_id))
        else:
            cursor.execute("""
                INSERT INTO application_executions (
                    job_id, platform, status, start_time, resume_used, error_reason,
                    profile_used, question_count, llm_question_count, profile_question_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.job_id, self.platform, status, now, self.resume_path, error_reason,
                  self.profile_type, self.telemetry.get("question_count", 0), self.telemetry.get("llm_question_count", 0), self.telemetry.get("profile_question_count", 0)))
        self.conn.commit()
        
        # Save submission proof to file if it exists
        if "submission_proof" in self.telemetry:
            import json
            import os
            proof_path = os.path.join(self.execution_dir, "submission_proof.json")
            try:
                os.makedirs(self.execution_dir, exist_ok=True)
                with open(proof_path, "w") as f:
                    json.dump(self.telemetry["submission_proof"], f, indent=4)
            except Exception as e:
                logger.info(f"Executor Error saving proof: {e}")

    def _log_early_abort_telemetry(self, status: str, reason: str):
        import os
        import csv
        telemetry_file = os.path.join(Config.DATA_DIR, "early_abort_telemetry.csv")
        file_exists = os.path.exists(telemetry_file)
        
        with open(telemetry_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "job_id", "company", "role", "scanner_result", "reason", "estimated_browser_time_saved_sec", "estimated_llm_calls_saved"])
            
            time_saved = 0
            llm_saved = 0
            if status in ["SKIPPED_INELIGIBLE", "REVIEW_REQUIRED"]:
                time_saved = 120 # Avg 2 mins filling forms
                llm_saved = 8    # Avg 8 RAG/LLM questions
                
            writer.writerow([
                datetime.datetime.now().isoformat(),
                self.job_id,
                self.company_name,
                self.job_title,
                status,
                reason,
                time_saved,
                llm_saved
            ])

    def execute(self):
        logger.info(f"Executor: Starting job {self.job_id} on {self.platform} ({self.url})")
        
        # DATABASE LOCKING & FINGERPRINT
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("BEGIN IMMEDIATE TRANSACTION")
            
            # Check for current job state
            cursor.execute("SELECT status FROM application_executions WHERE job_id = ?", (self.job_id,))
            row = cursor.fetchone()
            if row:
                if row['status'] in ['IN_PROGRESS', 'SUBMITTED']:
                    self.conn.commit()
                    logger.info(f"Executor: Job {self.job_id} is already {row['status']}. Skipping.")
                    return f"SKIPPED_ALREADY_{row['status']}"
                    
            # Check fingerprint
            cursor.execute("""
                SELECT ae.id FROM application_executions ae
                JOIN jobs j ON ae.job_id = j.id
                WHERE ae.status = 'SUBMITTED'
                AND j.company_name = ? AND j.job_title = ? AND j.job_url = ?
            """, (self.company_name, self.job_title, self.url))
            if cursor.fetchone():
                self.conn.commit()
                self.conn.commit()
                logger.info(f"Executor: Identical SUBMITTED record found for fingerprint. Skipping.")
                return "SKIPPED_ALREADY_SUBMITTED"
                
            # Pre-flight Eligibility Check
            cursor.execute("SELECT location, job_description FROM jobs WHERE id = ?", (self.job_id,))
            job_row = cursor.fetchone()
            if job_row:
                from src.jobs.eligibility_filter import EligibilityFilter
                eligibility = EligibilityFilter.check_eligibility(
                    job_location=job_row['location'],
                    job_description=job_row['job_description'],
                    profile_manager=self.profile
                )
                if not eligibility["is_eligible"]:
                    self.conn.commit()
                    reason = eligibility["skip_reason"]
                    logger.info(f"Executor: Job {self.job_id} failed eligibility check. Reason: {reason}")
                    self._log_early_abort_telemetry("SKIPPED_INELIGIBLE", reason)
                    return "SKIPPED_INELIGIBLE"
                
            # Set IN_PROGRESS
            now = datetime.datetime.now().isoformat()
            if row:
                cursor.execute("UPDATE application_executions SET status = 'IN_PROGRESS', start_time = ? WHERE job_id = ?", (now, self.job_id))
            else:
                cursor.execute("""
                    INSERT INTO application_executions (
                        job_id, platform, status, start_time, resume_used,
                        profile_used, question_count, llm_question_count, profile_question_count
                    )
                    VALUES (?, ?, 'IN_PROGRESS', ?, ?, ?, ?, ?, ?)
                """, (self.job_id, self.platform, now, self.resume_path,
                      self.profile_type, 0, 0, 0))
            self.conn.commit()
            
        except sqlite3.OperationalError as e:
            # If the database is locked by another process
            logger.info(f"Executor: Failed to acquire lock for job {self.job_id}: {e}")
            self.conn.rollback()
            return "SKIPPED_LOCKED"
        except Exception as e:
            logger.info(f"Executor: DB Error during locking: {e}")
            self.conn.rollback()
            return "FAILED"
            
        # Continue execution...
        
        if self.platform == "UNKNOWN":
            self.log_execution("REVIEW_REQUIRED", "Unknown Platform")
            logger.info("Executor: Paused - Unknown platform detected.")
            return "REVIEW_REQUIRED"
            
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.goto(self.url, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                
                # Check for interstitial blocking pages and CAPTCHAs
                title_lower = page.title().lower()
                has_captcha_frame = page.locator("iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[src*='cloudflare']").count() > 0
                if "just a moment" in title_lower or "attention required" in title_lower or "captcha" in title_lower or has_captcha_frame:
                    logger.info("Executor: Paused - Anti-Bot/CAPTCHA Protection detected.")
                    self.log_execution("REVIEW_REQUIRED", "CAPTCHA_DETECTED")
                    browser.close()
                    return "REVIEW_REQUIRED"
                    
                # EARLY ELIGIBILITY SCANNER V2
                from src.applications.early_abort import EarlyEligibilityScanner
                scanner = EarlyEligibilityScanner(self.profile)
                try:
                    page_text = page.locator('body').inner_text(timeout=5000)
                    scan_result = scanner.scan_page(page_text)
                    
                    if scan_result["status"] == "SKIPPED_INELIGIBLE":
                        logger.info(f"Executor: 🚫 EARLY ABORT - {scan_result['reason']}")
                        self.log_execution("SKIPPED_INELIGIBLE", scan_result['reason'])
                        self._log_early_abort_telemetry(scan_result["status"], scan_result['reason'])
                        browser.close()
                        return "SKIPPED_INELIGIBLE"
                    elif scan_result["status"] == "REVIEW":
                        logger.info(f"Executor: ⚠️ EARLY ABORT (REVIEW) - {scan_result['reason']}")
                        self.log_execution("REVIEW_REQUIRED", scan_result['reason'])
                        self._log_early_abort_telemetry(scan_result["status"], scan_result['reason'])
                        browser.close()
                        return "REVIEW_REQUIRED"
                    else:
                        self._log_early_abort_telemetry("OK", "Passed Early Scanner")
                except Exception as e:
                    logger.info(f"Executor: Early Eligibility Scanner failed to read page text: {e}")
                
                
                # Route to Handlers (Phase 1)
                if self.platform == "GREENHOUSE":
                    result = self._handle_greenhouse(page)
                elif self.platform == "LEVER":
                    result = self._handle_lever(page)
                elif self.platform == "ASHBY":
                    result = self._handle_ashby(page)
                else:
                    logger.info(f"Executor: Handler for {self.platform} not implemented yet.")
                    result = "REVIEW_REQUIRED"
                    self.log_execution(result, f"No Handler for {self.platform}")
                    
                browser.close()
                
                # FINAL EMAIL CONFIRMATION CHECK
                if result != "SUBMITTED":
                    logger.info(f"Executor: UI verification resulted in {result}. Checking for email confirmation...")
                    from src.applications.email_confirmation import EmailConfirmationChecker
                    if EmailConfirmationChecker.check_for_confirmation(self.company_name, self.job_title):
                        logger.info("Executor: Email confirmation found! Overriding status to SUBMITTED.")
                        result = "SUBMITTED"
                        self.log_execution("SUBMITTED", "Success verified via email")
                        
                return result
        except Exception as e:
            logger.info(f"Executor Error: {e}")
            self.log_execution("FAILED", str(e))
            return "FAILED"

    def _handle_greenhouse(self, page):
        from src.applications.handlers.greenhouse import GreenhouseHandler
        logger.info("Executor [Greenhouse]: Initializing Greenhouse Handler...")
        handler = GreenhouseHandler(
            page, 
            self.job_title, 
            self.company_name, 
            self.location, 
            self.resume_path,
            test_mode=self.test_mode,
            execution_dir=self.execution_dir,
            profile_manager=self.profile,
            rag_client=self.rag_client,
            llm_client=self.llm_client,
            company_context=self.company_context
        )
        result_data = handler.execute()
        self.audit_log = result_data.get("audit_log", [])
        
        # Save telemetry
        if "telemetry" in result_data:
            self.telemetry = result_data["telemetry"]
            
        error_reason = ""
        if "diagnosis_json" in self.telemetry:
            error_reason = self.telemetry["diagnosis_json"]
            self._log_submission_debug_telemetry(result_data["status"], error_reason, self.telemetry.get("repair_attempts", 0))
            
        self.log_execution(result_data["status"], error_reason)
        
        # FINAL FORENSIC SUMMARY
        logger.info("\n==================================================")
        logger.info("GREENHOUSE OTP FAILURE FORENSICS")
        t = self.telemetry
        if result_data["status"] == "SUBMITTED_CONFIRMED" or result_data["status"] == "SUBMITTED":
            logger.info("The automation stopped because success signals were confirmed.")
        elif t.get("otp_detected"):
            v2 = t.get("otp_forensics_v2", {})
            existed = v2.get("email_existed", False)
            logger.info(f"Did the OTP email exist? {'YES' if existed else 'NO'}")
            
            if existed:
                reason = v2.get("extraction_failed_reason", "Unknown reason.")
                logger.info(f"Why extraction failed: {reason}")
            else:
                waited = v2.get("waited_seconds", 0)
                logger.info(f"How long we waited: {waited} seconds.")
                if waited < 120:
                    logger.info("Whether increasing timeout would solve it: Likely. 70s total might be too short for some providers.")
                else:
                    logger.info("Whether increasing timeout would solve it: Unlikely. We waited a long time.")
            
            logger.info("---")
            if not t.get("otp_received") and not existed:
                logger.info("The automation stopped because OTP Retrieval failed from IMAP after max retries (Email never arrived).")
            elif not t.get("otp_received") and existed:
                logger.info("The automation stopped because OTP Retrieval failed (Email arrived but parsing failed).")
            elif t.get("otp_received") and not t.get("otp_submitted"):
                logger.info("The automation stopped because OTP was received but an error occurred while filling the fields.")
            elif t.get("otp_submitted") and not t.get("otp_verified"):
                logger.info("The automation stopped because OTP was filled but the submit button was disabled or timed out.")
            else:
                logger.info("The automation stopped because OTP was submitted but validation errors appeared on the page.")
        else:
            logger.info("The automation stopped because it encountered a generic validation error or failure before reaching OTP.")
        logger.info("==================================================\n")
        
        return result_data["status"]

    def _log_submission_debug_telemetry(self, final_status: str, diagnosis_json: str, repair_attempts: int):
        import os
        import csv
        telemetry_file = os.path.join(Config.DATA_DIR, "submission_debug_telemetry.csv")
        file_exists = os.path.exists(telemetry_file)
        
        with open(telemetry_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "job_id", "company", "role", "diagnosis_json", "repair_attempts", "learning_log_json", "final_status"])
            import json
            learning_log = self.telemetry.get("learning_log", [])
            writer.writerow([
                datetime.datetime.now().isoformat(),
                self.job_id, self.company_name, self.job_title,
                diagnosis_json, repair_attempts, json.dumps(learning_log), final_status
            ])

    def _handle_lever(self, page):
        logger.info("Executor [Lever]: Looking for apply button...")
        try:
            page.locator('a.postings-btn').first.click(timeout=5000)
        except:
            pass
            
        logger.info("Executor [Lever]: Attempting to fill standard profile...")
        self.log_execution("REVIEW_REQUIRED", "Lever Human Review Gate")
        return "REVIEW_REQUIRED"

    def _handle_ashby(self, page):
        logger.info("Executor [Ashby]: Attempting to fill standard profile...")
        self.log_execution("REVIEW_REQUIRED", "Ashby Human Review Gate")
        return "REVIEW_REQUIRED"
