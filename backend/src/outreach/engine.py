from src.system.logger import setup_logger
logger = setup_logger('engine')
import os
import re
import glob
import pandas as pd
import sqlite3
import time
import json
import random
from datetime import datetime, timezone, timedelta
from groq import Groq
from src.utils.groq_manager import GroqManager
from src.config.config import Config
from src.outreach.email_client import EmailClient
from src.outreach.prompts import TEMPLATE_GENERATION_PROMPT
from src.utils.profile_parser import ProfileParser
from src.utils.llm_router import LLMRouter

IST_TZ = timezone(timedelta(hours=5, minutes=30))

def get_ist_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST_TZ)

def get_window_bounds_ist() -> tuple[datetime, datetime]:
    now = get_ist_now()
    start_dt = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_dt = now.replace(hour=15, minute=0, second=0, microsecond=0)
    return start_dt, end_dt

class OutreachEngine:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.client_manager = LLMRouter()
        self.email_client = EmailClient()
        self.limit = 400
        self.profile_parser = ProfileParser()
        self.contacted_in_session = set()

    def get_latest_excel(self):
        search_pattern = os.path.join(Config.DATA_DIR, "*.xlsx")
        files = glob.glob(search_pattern)
        if not files:
            return None
            
        priority = ["verified_active_leads.xlsx", "clean_leads.xlsx", "leads.xlsx", "leads_cleaned.xlsx", "Gend phad HR data.xlsx"]
        for p in priority:
            for f in files:
                if p in f: return f
                
        # Fallback to latest
        return max(files, key=os.path.getmtime)

    def generate_email(self, recruiter_name, company, role, notes, domain, project, intel_dict, email=""):
        # Sanitize company and role against 'nan' or empty values
        comp_str = str(company).strip() if company else ""
        if not comp_str or comp_str.lower() == 'nan':
            if domain and '.' in str(domain):
                comp_str = str(domain).split('.')[0].replace('-', ' ').replace('_', ' ').title()
            else:
                comp_str = "Your Team"
                
        role_str = str(role).strip() if role else ""
        if not role_str or role_str.lower() == 'nan':
            role_str = "Engineering Team"

        clean_name = str(recruiter_name).strip() if recruiter_name else ""
        if (not clean_name or clean_name.lower() in ['nan', 'none', 'hiring team', 'talent acquisition team', 'recruiter', 'team']) and email:
            user_part = email.split('@')[0].lower()
            generic_words = {'careers', 'talent', 'hr', 'jobs', 'recruiting', 'contact', 'info', 'apply', 'support', 'help', 'admin'}
            if not any(g in user_part for g in generic_words):
                name_candidate = re.split(r'[._-]', user_part)[0]
                if len(name_candidate) >= 3 and name_candidate.isalpha():
                    clean_name = name_candidate.capitalize()

        if clean_name and clean_name.lower() not in ['nan', 'none', 'hiring team', 'talent acquisition team', 'recruiter', 'team']:
            first_name = re.sub(r'[^a-zA-Z]', '', clean_name.split()[0]).capitalize()
            greeting = f"Hi {first_name}," if len(first_name) >= 2 else "Hello Hiring Team,"
        else:
            greeting = "Hello Hiring Team,"
        
        tailored_context = self.profile_parser.get_tailored_context(project)
        
        prompt = f"""
        {TEMPLATE_GENERATION_PROMPT}
        
        Company: {comp_str}
        Recipient Role: {role_str}
        Company Domain: {domain}
        Company Intelligence: {json.dumps(intel_dict)}
        Selected Project to Highlight: {project}
        
        --- YASH TAILORED PROFILE CONTEXT ---
        {tailored_context}
        """
        
        obs = ""
        rel = ""
        success = False
        for attempt in range(3):
            try:
                response = self.client_manager.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    intent="outreach"
                )
                raw_content = response.choices[0].message.content.strip()
                if "```json" in raw_content:
                    raw_content = raw_content.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_content:
                    raw_content = raw_content.split("```")[1].strip()
                data = json.loads(raw_content)
                obs = data.get("observation", "").replace("aligns with", "matches").replace("thrilled", "glad")
                rel = data.get("relevance", "").replace("aligns with", "matches").replace("thrilled", "glad")
                success = True
                break
            except Exception as e:
                logger.info(f"Outreach generation attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(6)
        
        if not success or not obs or not rel:
            return "", ""
            
        networking_asks = [
            "I'd love to learn more about the problems your team is solving.",
            "I'd be happy to connect if my background seems relevant.",
            "If you're open to it, I'd love to hear more about your team's current technical priorities.",
            "I would be glad to connect and learn more about the engineering challenges you are tackling.",
            "If my background matches any early-career opportunities, I'd be glad to connect."
        ]
        ask = random.choice(networking_asks)
        
        # Construct final template
        body = f"""{greeting}

I'm a recent IIT Roorkee graduate focused on AI systems and product development. {obs}

{rel}

{ask}

Best,
Yash Kherwal
B.Tech, IIT Roorkee
Phone: +91 9891148156
Email: yash.kherwal78@gmail.com
LinkedIn: linkedin.com/in/yash-kherwal-944497254"""

        if role_str and role_str != "Engineering Team":
            subject = f"Connecting: {role_str} / IIT Roorkee"
        else:
            subject = f"Connecting: IIT Roorkee Student & {comp_str} Opportunities"

        return subject, body

    def is_already_contacted(self, email: str) -> bool:
        clean_email = email.strip().lower()
        if clean_email in self.contacted_in_session:
            return True
            
        db_paths = set([
            str(Config.DATABASE_PATH),
            os.path.join(str(Config.DATA_DIR), "crm.db"),
            os.path.join(os.path.dirname(str(Config.DATA_DIR)), "backend", "data", "crm.db")
        ])
        
        for path in db_paths:
            if not os.path.exists(path):
                continue
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM outreach_log WHERE LOWER(TRIM(email)) = ? AND status = 'SENT'", (clean_email,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.contacted_in_session.add(clean_email)
                    return True
            except Exception as e:
                logger.info(f"Error checking duplicate in {path}: {e}")
                
        return False

    def log_outreach(self, email, name, company, role, subject, body, status):
        clean_email = email.strip().lower()
        if status == "SENT":
            self.contacted_in_session.add(clean_email)
            
        db_paths = set([
            str(Config.DATABASE_PATH),
            os.path.join(str(Config.DATA_DIR), "crm.db"),
            os.path.join(os.path.dirname(str(Config.DATA_DIR)), "backend", "data", "crm.db")
        ])
        
        now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for path in db_paths:
            if not os.path.exists(os.path.dirname(path)):
                continue
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO outreach_log (email, recruiter_name, company, role, subject, body, status, sent_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (email.strip(), name, company, role, subject, body, status, now_ts))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.info(f"Error logging outreach in {path}: {e}")

    def generate_report(self, processed, sent, skipped, failures):
        report_path = os.path.join(Config.DATA_DIR, "daily_outreach_report.md")
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(report_path, "w") as f:
            f.write("# Daily Outreach Report\n")
            f.write(f"Date: {timestamp}\n\n")
            f.write(f"- Emails Processed: {processed}\n")
            f.write(f"- Emails Sent: {sent}\n")
            f.write(f"- Duplicates Skipped: {skipped}\n")
            f.write(f"- Failures: {failures}\n\n")
            f.write("## Token Usage\n")
            f.write("Token usage is now tracked centrally in the llm_usage_log database table.\n")
            
        # STEP 7: TELEMETRY (Permanent Log)
        telemetry_path = os.path.join(Config.DATA_DIR, "daily_outreach_telemetry.csv")
        file_exists = os.path.isfile(telemetry_path)
        with open(telemetry_path, "a") as f:
            if not file_exists:
                f.write("Timestamp,Scheduler Triggered,Prospects Found,Messages Generated,Messages Sent,Failures\n")
            # Prospects Found = processed + skipped
            # Messages Generated = sent + failures (roughly)
            # Scheduler Triggered is implicit
            f.write(f"{timestamp},Yes,{processed + skipped},{processed},{sent},{failures}\n")
            
    def run_daily_batch(self):
        from src.intelligence.intelligence import run_intelligence_engine
        from src.intelligence.project_selector import ProjectSelector
        from src.outreach.critic import EmailCritic
        from src.outreach.email_client import ResumeAttachmentError
        from src.outreach.email_generation_graph import run_generation_loop
        
        critic = EmailCritic()
        logger.info("Starting Autonomous Outreach Engine V2...")
        excel_path = self.get_latest_excel()
        if not excel_path:
            logger.info("No Excel file found in data/")
            return
            
        logger.info(f"Loading {excel_path}")
        try:
            df = pd.read_excel(excel_path)
            # Standardize columns and deduplicate headers
            col_map = {c: str(c).lower().strip() for c in df.columns}
            df.rename(columns=col_map, inplace=True)
            df = df.loc[:, ~df.columns.duplicated()]
            
            email_col = next((c for c in df.columns if 'email' in c), None)
            name_col = next((c for c in df.columns if 'name' in c and 'company' not in c), None)
            company_col = next((c for c in df.columns if 'company' in c), None)
            role_col = next((c for c in df.columns if 'role' in c or 'title' in c), None)
            notes_col = next((c for c in df.columns if 'note' in c), None)
            
            if not email_col:
                logger.info("Could not find email column.")
                return
                
        except Exception as e:
            logger.info(f"Error reading Excel: {e}")
            return
            
        processed, sent, skipped, failures = 0, 0, 0, 0

        def _safe_str(val):
            if hasattr(val, 'dropna'):
                s = val.dropna()
                return str(s.iloc[0]).strip() if not s.empty else ""
            if pd.isna(val):
                return ""
            return str(val).strip()
        
        for _, row in df.iterrows():
            now_ist = get_ist_now()
            start_window, end_window = get_window_bounds_ist()
            
            # If current time is before 9:00 AM IST, wait until 9:00 AM IST
            if now_ist < start_window:
                wait_sec = (start_window - now_ist).total_seconds()
                logger.info(f"Current time ({now_ist.strftime('%H:%M:%S')} IST) is before 9:00 AM IST. Waiting {wait_sec/60:.1f} mins until window opens...")
                time.sleep(min(wait_sec, 600))
                continue
                
            # If current time is past 3:00 PM IST (15:00), window is closed for the day
            if now_ist >= end_window:
                logger.info(f"3:00 PM IST reached ({now_ist.strftime('%H:%M:%S')} IST). Outreach window is closed for today. Stopping.")
                break

            if sent >= self.limit:
                logger.info("Reached daily limit.")
                break
                
            email_val = _safe_str(row.get(email_col, ""))
            if not email_val or email_val.lower() == 'nan':
                continue
                
            processed += 1
            if self.is_already_contacted(email_val):
                logger.info(f"Skipping {email_val} - Already contacted.")
                skipped += 1
                continue
                
            name_val = _safe_str(row.get(name_col, "")) if name_col else ""
            company_val = _safe_str(row.get(company_col, "")) if company_col else ""
            if not company_val or company_val.lower() == 'nan':
                if '@' in email_val:
                    company_val = email_val.split('@')[1].split('.')[0].replace('-', ' ').title()
                else:
                    company_val = "Your Team"

            role_val = _safe_str(row.get(role_col, "")) if role_col else ""
            if not role_val or role_val.lower() == 'nan':
                role_val = "Engineering"
            notes_val = _safe_str(row.get(notes_col, "")) if notes_col else ""

            # Pre-Send Zero-Bounce Verification Guard
            from src.outreach.email_verifier import verifier
            v_res = verifier.verify_email(email_val)
            if not v_res.get("deliverable", False):
                logger.info(f"Skipping {email_val} - Dead Mailbox ({v_res.get('status')}): {v_res.get('reason')}")
                skipped += 1
                self.log_outreach(email_val, name_val, company_val, role_val, "", "", f"DEAD_SKIPPED: {v_res.get('status')}")
                continue

            logger.info(f"Processing verified lead {email_val} at {company_val} (Status: {v_res.get('status')})...")
            
            # 1. Company Intelligence
            intel = run_intelligence_engine(company_val)
            domain = intel.get("domain", "Other")
            
            project, proj_rejected, proj_reason, proj_conf = ProjectSelector.select(company_val, intel)
            
            # 3. Email Generation & Critic Loop -- a LangGraph StateGraph
            # (backend/src/outreach/email_generation_graph.py), not a plain
            # Python loop: this is the one place in the codebase where a
            # runtime outcome (did the critic pass?) actually decides what
            # happens next, which is what conditional graph edges are for.
            subject, body, critic_result, critic_passed = run_generation_loop(
                self, critic, name_val, company_val, role_val, notes_val,
                domain, project, intel, email_val, max_attempts=3,
            )

            if not critic_passed:
                logger.info(f"Failed to pass Email Critic for {email_val}. Skipping.")
                failures += 1
                if failures >= 5:
                    logger.info("Consecutive LLM failures (likely API rate limit). Pausing for 60s to let cooldown expire...")
                    time.sleep(60)
                    failures = 0
                continue
            else:
                failures = 0  # Reset on success
                
            # 4. Resume Attachment (Fixed Outreach Resume)
            resume_path = str(Config.DATA_DIR / "OUTREACH_RESUME.pdf")
            if not os.path.exists(resume_path):
                # Fallback only if the user hasn't added it yet
                resume_path = str(Config.DATA_DIR / "Resume_aiml.pdf")
            
            # 5. Trace Mode / Send Email
            if getattr(Config, "OUTREACH_TRACE_MODE", False):
                logger.info(f"--- TRACE MODE ACTIVATED for {company_val} ---")
                word_count = len(body.split())
                trace_path = Config.DATA_DIR / "outreach_trace_report.md"
                with open(trace_path, "a") as f:
                    f.write(f"\n## Trace for {company_val}\n")
                    f.write(f"**Domain:** {domain}\n")
                    f.write(f"**Industry:** {intel.get('industry', 'Unknown')}\n")
                    f.write(f"**Selected Project:** {project}\n")
                    f.write(f"**Rejected Projects:** {', '.join(proj_rejected)}\n")
                    f.write(f"**Reasoning:** {proj_reason}\n")
                    f.write(f"**Confidence:** {proj_conf}\n")
                    f.write(f"**Critic Overall Score:** {critic_result.get('Overall Score', 'N/A')}\n")
                    f.write(f"**Critic Status:** {'PASS' if critic_passed else 'FAIL'}\n")
                    f.write(f"**Critic Details:**\n")
                    for k, v in critic_result.items():
                        if k not in ['Overall Score', 'status', 'reason']:
                            f.write(f"  - {k}: {v}\n")
                    f.write(f"**Critic Feedback:** {critic_result.get('reason', 'None')}\n")
                    f.write(f"**Word Count:** {word_count}\n")
                    f.write(f"**Final Email Subject:** {subject}\n")
                    f.write(f"**Final Email Body:**\n```\n{body}\n```\n")
                    f.write("---\n")
                continue # Skip actual sending
                
            success = False
            attachment_status = "OK"
            try:
                if self.email_client.send_email(email_val, subject, body, resume_path=resume_path, dry_run=self.dry_run):
                    success = True
            except (ResumeAttachmentError, ValueError) as e:
                logger.info(f"Pre-send Validation Failed: {e}")
                attachment_status = f"FAILED: {e}"
                success = False
            except Exception as e:
                logger.info(f"Send Failed for {email_val}: {e}")
                attachment_status = f"FAILED: {e}"
                success = False
                
            status = "SENT" if success else "FAILED"
            
            # Trace Logging
            logger.info(f"--- TRACE LOG ---")
            logger.info(f"Company: {company_val}")
            logger.info(f"Domain: {domain}")
            logger.info(f"Selected Project: {project}")
            logger.info(f"Critic Result: PASS")
            logger.info(f"Resume Path: {resume_path}")
            logger.info(f"Attachment Status: {attachment_status}")
            logger.info(f"Send Status: {status}")
            logger.info(f"-----------------")
            
            if not self.dry_run:
                self.log_outreach(email_val, name_val, company_val, role_val, subject, body, status)
                
            if success:
                sent += 1
                logger.info(f"🚀 [OUTREACH PROGRESS: {sent}/{self.limit} SUCCESSFUL MAILS SENT] (Skipped: {skipped})")
                if not self.dry_run and sent < self.limit:
                    now_ist = get_ist_now()
                    _, end_window = get_window_bounds_ist()
                    rem_sec = max(0, (end_window - now_ist).total_seconds())
                    rem_mails = max(1, self.limit - sent)
                    if rem_sec > 0:
                        ideal_pace = (rem_sec / rem_mails) - 5.0
                        sleep_sec = max(35.0, min(60.0, ideal_pace + random.uniform(-3.0, 3.0)))
                    else:
                        sleep_sec = random.uniform(45.0, 55.0)
                    logger.info(f"Pacing delay (9 AM – 3 PM IST window): sleeping {sleep_sec:.1f}s before next recipient...")
                    time.sleep(sleep_sec)
            else:
                failures += 1
            
        self.generate_report(processed, sent, skipped, failures)
        logger.info("Daily Outreach V2 complete.")
