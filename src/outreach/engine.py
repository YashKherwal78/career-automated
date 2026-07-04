import os
import glob
import pandas as pd
import sqlite3
import time
import json
import random
from datetime import datetime
from groq import Groq
from src.utils.groq_manager import GroqManager
from src.config.config import Config
from src.outreach.email_client import EmailClient
from src.outreach.prompts import TEMPLATE_GENERATION_PROMPT
from src.utils.profile_parser import ProfileParser
from src.utils.llm_router import LLMRouter

class OutreachEngine:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.client_manager = LLMRouter()
        self.email_client = EmailClient()
        self.limit = 400
        self.profile_parser = ProfileParser()

    def get_latest_excel(self):
        search_pattern = os.path.join(Config.DATA_DIR, "*.xlsx")
        files = glob.glob(search_pattern)
        if not files:
            return None
            
        priority = ["clean_leads.xlsx", "leads.xlsx", "leads_cleaned.xlsx", "Gend phad HR data.xlsx"]
        for p in priority:
            for f in files:
                if p in f: return f
                
        # Fallback to latest
        return max(files, key=os.path.getmtime)

    def generate_email(self, recruiter_name, company, role, notes, domain, project, intel_dict):
        greeting = f"Hi {recruiter_name.split()[0]}," if recruiter_name.strip() else "Hello Hiring Team,"
        
        tailored_context = self.profile_parser.get_tailored_context(project)
        
        prompt = f"""
        {TEMPLATE_GENERATION_PROMPT}
        
        Company: {company}
        Company Domain: {domain}
        Company Intelligence: {json.dumps(intel_dict)}
        Selected Project to Highlight: {project}
        
        --- YASH TAILORED PROFILE CONTEXT ---
        {tailored_context}
        """
        
        try:
            response = self.client_manager.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
                intent="outreach"
            )
            data = json.loads(response.choices[0].message.content)
            obs = data.get("observation", "")
            rel = data.get("relevance", "")
            
            networking_asks = [
                "I'd love to learn more about the problems your team is solving.",
                "I'd be happy to connect if my background seems relevant.",
                "If you're open to it, I'd love to hear more about your team's current technical priorities.",
                "I would be thrilled to connect and learn more about the engineering challenges you are tackling.",
                "If my background aligns with any early-career opportunities, I'd be glad to connect."
            ]
            ask = random.choice(networking_asks)
            
            # Construct final template
            body = f"""{greeting}

I'm a final-year IIT Roorkee student focused on AI systems and product development. {obs}

{rel}

{ask}

Best,
Yash Kherwal
B.Tech, IIT Roorkee
Phone: +91 9891148156
Email: yash.kherwal78@gmail.com
LinkedIn: linkedin.com/in/yash-kherwal-944497254"""

            subject = f"Connecting: IIT Roorkee Student & {company} Opportunities"
            if role:
                subject = f"Connecting: {role} / IIT Roorkee"

            return subject, body
        except Exception as e:
            print(f"Error generating email parts: {e}")
            return "", ""

    def is_already_contacted(self, email: str) -> bool:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM outreach_log WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return bool(row)

    def log_outreach(self, email, name, company, role, subject, body, status):
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO outreach_log (email, recruiter_name, company, role, subject, body, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (email, name, company, role, subject, body, status))
        conn.commit()
        conn.close()

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
        
        critic = EmailCritic()
        print("Starting Autonomous Outreach Engine V2...")
        excel_path = self.get_latest_excel()
        if not excel_path:
            print("No Excel file found in data/")
            return
            
        print(f"Loading {excel_path}")
        try:
            df = pd.read_excel(excel_path)
            # Standardize columns
            col_map = {c: c.lower().strip() for c in df.columns}
            df.rename(columns=col_map, inplace=True)
            
            email_col = next((c for c in df.columns if 'email' in c), None)
            name_col = next((c for c in df.columns if 'name' in c and 'company' not in c), None)
            company_col = next((c for c in df.columns if 'company' in c), None)
            role_col = next((c for c in df.columns if 'role' in c or 'title' in c), None)
            notes_col = next((c for c in df.columns if 'note' in c), None)
            
            if not email_col:
                print("Could not find email column.")
                return
                
        except Exception as e:
            print(f"Error reading Excel: {e}")
            return
            
        processed, sent, skipped, failures = 0, 0, 0, 0
        
        for _, row in df.iterrows():
            if sent >= self.limit:
                print("Reached daily limit.")
                break
                
            email_val = str(row.get(email_col, "")).strip()
            if not email_val or email_val.lower() == 'nan':
                continue
                
            processed += 1
            if self.is_already_contacted(email_val):
                print(f"Skipping {email_val} - Already contacted.")
                skipped += 1
                continue
                
            name_val = str(row.get(name_col, "")) if name_col else ""
            company_val = str(row.get(company_col, "")) if company_col else ""
            role_val = str(row.get(role_col, "")) if role_col else ""
            notes_val = str(row.get(notes_col, "")) if notes_col else ""
            
            print(f"Processing {email_val} at {company_val}...")
            
            # 1. Company Intelligence
            intel = run_intelligence_engine(company_val)
            domain = intel.get("domain", "Other")
            
            # 2. Project Selection
            project, proj_rejected, proj_reason, proj_conf = ProjectSelector.select(domain)
            
            # 3. Email Generation & Critic Loop
            subject, body = "", ""
            critic_passed = False
            critic_result = {}
            for attempt in range(3):
                subject, body = self.generate_email(name_val, company_val, role_val, notes_val, domain, project, intel)
                if not body:
                    continue
                    
                critic_result = critic.evaluate(body, company_val, project, domain)
                if critic_result.get("status") == "PASS":
                    critic_passed = True
                    break
                else:
                    print(f"Critic Rejected Attempt {attempt+1}: {critic_result.get('reason')}")
                    
            if not critic_passed:
                print(f"Failed to pass Email Critic for {email_val}. Skipping.")
                failures += 1
                if failures >= 5:
                    print("Too many consecutive failures. Aborting batch early due to likely API rate limits.")
                    break
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
                print(f"--- TRACE MODE ACTIVATED for {company_val} ---")
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
                    f.write(f"**Critic Score:** {'PASS' if critic_passed else 'FAIL'}\n")
                    f.write(f"**Critic Feedback:** {critic_result.get('reason', 'None')}\n")
                    f.write(f"**Word Count:** {word_count}\n")
                    f.write(f"**Final Email Subject:** {subject}\n")
                    f.write(f"**Final Email Body:**\n```\n{body}\n```\n")
                    f.write("---\n")
                continue # Skip actual sending
                
            success = False
            attachment_status = "OK"
            try:
                for attempt in range(3):
                    if self.email_client.send_email(email_val, subject, body, resume_path=resume_path, dry_run=self.dry_run):
                        success = True
                        break
                    time.sleep(2)
            except (ResumeAttachmentError, ValueError) as e:
                print(f"Pre-send Validation Failed: {e}")
                attachment_status = f"FAILED: {e}"
                success = False
                
            status = "SENT" if success else "FAILED"
            
            # Trace Logging
            print(f"--- TRACE LOG ---")
            print(f"Company: {company_val}")
            print(f"Domain: {domain}")
            print(f"Selected Project: {project}")
            print(f"Critic Result: PASS")
            print(f"Resume Path: {resume_path}")
            print(f"Attachment Status: {attachment_status}")
            print(f"Send Status: {status}")
            print(f"-----------------")
            
            if not self.dry_run or True: 
                self.log_outreach(email_val, name_val, company_val, role_val, subject, body, status)
                
            if success: sent += 1
            else: failures += 1
            
        self.generate_report(processed, sent, skipped, failures)
        print("Daily Outreach V2 complete.")
