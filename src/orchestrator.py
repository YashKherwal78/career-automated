from src.system.logger import setup_logger
logger = setup_logger('orchestrator')
import os
import json
import random
import sqlite3
from datetime import datetime
from src.config.config import Config
from src.referrals.pipeline import run_referral_engine
from groq import Groq
from src.crm.database import add_or_update_lead, get_lead
from src.crm.state_machine import CRMState, transition_state
from src.intelligence.intelligence import run_intelligence_engine
from src.enrichment.enrichment import enrich_company
from src.jobs.matching import run_job_matching
from src.resume.agent5_resume_tailor import tailor_resume
from src.outreach.strategy import generate_email_strategy
from src.outreach.prompts import HR_SYSTEM_PROMPT, FOUNDER_SYSTEM_PROMPT, EMAIL_CRITIC_PROMPT
from src.outreach.human_review_gate import human_review_gate
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

groq_client = Groq(api_key=Config.GROQ_API_KEY)

def send_email(to_email, subject, body, resume_path):
    msg = MIMEMultipart()
    msg['From'] = Config.GMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with open(resume_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename="Yash_Kherwal_Resume.pdf")
            msg.attach(attach)
    except Exception as e:
        logger.info(f"Could not attach resume: {e}")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logger.info(f"❌ Failed to send email: {e}")
        return False

def run_outreach_for_job(job_id: int, lead: dict, mc):
    logger.info(f"\n=======================================================")
    logger.info(f"🚀 RECRUITING INTELLIGENCE PLATFORM: Processing Job ID {job_id}")
    logger.info(f"=======================================================")
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        # Fallback for leads imported without a specific job
        job = {
            "company_name": lead["company_name"],
            "job_title": "Software Engineer",
            "job_description": "We are looking for a software engineer to build scalable AI systems, work on backend infrastructure, and improve data processing.",
            "days_old": 0
        }
        
    company_name = job["company_name"]
    job_desc = job["job_description"]
    
    lead = get_lead(company_name)
    if not lead:
        logger.info(f"[{company_name}] Lead not found in CRM. Skipping.")
        return False
        
    # Hardcode AI Resume as requested by user
    resume_family = "AI Resume"

    # Re-initialize client inside to avoid unbound local error when we overwrite it
    active_groq_client = Groq(api_key=Config.GROQ_API_KEY)

    # AGENT 1: Intelligence (Resume Strategy)
    logger.info("\n[Agent 1] Intelligence Engine (Resume Strategy & Company classification)...")
    metadata = run_intelligence_engine(active_groq_client, company_name)
    transition_state(company_name, CRMState.SCORED)
    
    # AGENT 5: Resume Tailoring
    logger.info("\n[Agent 5] Resume Tailoring Engine...")
    
    # Determine base template
    rec_resume = job.get("recommended_resume", "AIML_RESUME")
    if rec_resume == "PRODUCT_RESUME":
        base_resume = str(Config.DATA_DIR / "yash_resume_pm.tex")
    else:
        # For DATA, AI, SWE, default to AIML_RESUME template for now
        base_resume = str(Config.DATA_DIR / "yash_resume_aiml.tex")
        
    tailored_resume_path, selected_project = tailor_resume(active_groq_client, base_resume, company_name, job["job_title"], job_desc, job_id)
    transition_state(company_name, CRMState.RESUME_TAILORED)
    
    # ENRICHMENT OPTIMIZATION: Contact Discovery
    logger.info("\n[Agent 2] Contact Discovery Engine...")
    enrichment_data = enrich_company(company_name)
    metadata.update(enrichment_data)
    transition_state(company_name, CRMState.ENRICHED)
    
    # We must update lead dict with enrichment data for Mission Control validation
    lead.update(enrichment_data)
    
    # AGENT 7: Email Strategy
    logger.info("\n[Agent 7] Email Strategy Engine...")
    strategy = generate_email_strategy(active_groq_client, company_name, job_desc, selected_project)
    
    # AGENT 8 & 9: Email Writer & Critic
    logger.info("\n[Agent 8 & 9] Email Writer Engine & Critic Loop...")
    # Load context for Agent 8
    try:
        with open(Config.DATA_DIR / "context" / "yash_master_profile.md", "r") as f:
            yash_master_profile = f.read()
        context_str = f"\n\n--- YASH MASTER PROFILE ---\n{yash_master_profile}"
    except Exception:
        context_str = ""

    subject_variant = "IIT Roorkee Student | " + job["job_title"]
    
    max_attempts = 3
    email_data = {}
    critic_data = {}
    
    for attempt in range(max_attempts):
        logger.info(f"Agent 8: Generating Email (Attempt {attempt+1}/{max_attempts})...")
        try:
            response = active_groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": HR_SYSTEM_PROMPT + context_str},
                    {"role": "user", "content": f"Target Company: {company_name}\nJob Role: {job['job_title']}\nStrategy: {json.dumps(strategy)}\nForced Subject: {subject_variant}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            email_data = json.loads(response.choices[0].message.content)
            draft_body = email_data.get("body", "")
            
            logger.info(f"Agent 9: Critiquing Email Draft...")
            critic_response = active_groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": EMAIL_CRITIC_PROMPT},
                    {"role": "user", "content": f"Please evaluate the following email draft:\n\n{draft_body}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            critic_data = json.loads(critic_response.choices[0].message.content)
            
            if critic_data.get("status") == "PASS":
                logger.info("Agent 9: PASS. Email looks authentic.")
                break
            else:
                logger.info(f"Agent 9: FAIL. Feedback: {critic_data.get('feedback')}")
        except Exception as e:
            if "429" in str(e) and getattr(Config, "GROQ_API_KEY_BACKUP", ""):
                logger.info(f"Rate limit hit! Switching to backup API key for attempt {attempt+2}...")
                active_groq_client = Groq(api_key=Config.GROQ_API_KEY_BACKUP)
                continue
            logger.info(f"Error during email generation/critique: {e}")
            break
            
    subject = email_data.get("subject", subject_variant)
    body = email_data.get("body", "")
    
    # Store Agent 8 explainability
    lead_db = get_lead(company_name)
    agent_metadata_str = lead_db.get("agent_metadata", "{}") if lead_db else "{}"
    try:
        meta_db = json.loads(agent_metadata_str)
    except:
        meta_db = {}
    meta_db["email_writer"] = {
        "decision": email_data.get("decision", "Generated Email"),
        "confidence": email_data.get("confidence", 0.9),
        "reasoning": email_data.get("reasoning", "Followed strategy"),
        "critic_status": critic_data.get("status", "UNKNOWN"),
        "critic_feedback": critic_data.get("feedback", "")
    }
    add_or_update_lead(company_name, {"agent_metadata": json.dumps(meta_db)})
    
    if critic_data.get("status") == "FAIL":
        logger.info(f"Agent 9 Final Verdict: FAILED after {max_attempts} attempts. Transitioning to REVIEW_REQUIRED.")
        transition_state(company_name, CRMState.REVIEW_REQUIRED)
        return False
        
    # Pass final generated email to lead dict for validation
    lead["generated_email_subject"] = subject
    lead["generated_email_body"] = body

    # MISSION CONTROL V1 GATE
    logger.info("\n[Mission Control] Validating Rules...")
    rule_decision = mc.validate_rules(lead)
    
    if rule_decision == "SKIP_DAILY_LIMIT":
        logger.info("❌ Skipped: Daily Limit Reached.")
        return False
    elif rule_decision == "SKIP_BOUNCE_LIMIT" or rule_decision == "SKIP_LOW_PROB":
        logger.info(f"❌ Skipped by Mission Control Rules ({rule_decision}).")
        add_or_update_lead(company_name, {"status": "Rejected by Mission Control"})
        return False
        
    final_decision = "PROCEED"
    if rule_decision == "LLM_REVIEW":
        llm_eval = mc.llm_validation(lead)
        final_decision = llm_eval.get("decision", "SKIP")
        logger.info(f"[Mission Control] LLM Validation returned: {final_decision}. Reasoning: {llm_eval.get('reasoning')}")
        
    if final_decision == "PROCEED":
        target_email = enrichment_data.get("target_email")
        if target_email:
            logger.info(f"🚀 LIVE DISPATCH: Sending to {target_email}...")
            
            # Transition to Outbox Queue to protect against Gmail failure
            transition_state(company_name, CRMState.OUTBOX_QUEUE)
            
            success = send_email(target_email, subject, body, tailored_resume_path)
            
            if success:
                add_or_update_lead(company_name, {
                    "status": "HR Contacted", 
                    "hr_contacted": 1, 
                    "hr_contact_date": datetime.now().isoformat()
                })
                transition_state(company_name, CRMState.HR_CONTACTED)
            else:
                logger.info("❌ Failed to dispatch email. Kept in OUTBOX_QUEUE.")
                return False
                
            return {
                "job_title": job["job_title"],
                "company_name": company_name,
                "job_match_score": job_match.get("job_match_score", lead.get("job_match_score")),
                "interview_probability": lead.get("interview_probability"),
                "selected_resume": resume_family,
                "selected_project": strategy.get("selected_project", "N/A"),
                "selected_contact": target_email,
                "generated_email": body
            }
        else:
            logger.info("❌ Approval granted, but no target email address found in CRM Enrichment.")
    else:
        logger.info("❌ Outreach Rejected at Mission Control Gate.")
    return None

def run_batch_operations():
    from src.mission_control.mission_control import MissionControl
    from src.jobs.discovery import ingest_jobs
    from src.crm.database import get_all_uncontacted_scored_leads
    
    logger.info("\n[Mission Control] Initializing Daily Operations...")
    mc = MissionControl()
    
    # 1. Daily Job Discovery (Using CSV for local test since Apify quota exceeded)
    ingest_jobs("csv")
    
    # 2. Score un-matched jobs
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = 'New'")
    new_leads = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    for lead in new_leads:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT job_description, days_old FROM jobs WHERE id = ?", (lead['job_id'],))
        job = cursor.fetchone()
        conn.close()
        
        if not job: 
            job = {
                "job_title": "Software Engineer",
                "job_description": "We are looking for a software engineer to build scalable AI systems, work on backend infrastructure, and improve data processing.",
                "days_old": 0
            }
        
        logger.info(f"\n[Agent 3] Job Matching & Scoring Engine for {lead['company_name']}...")
        match_data = run_job_matching(groq_client, lead['company_name'], lead['job_id'] or 0, job['job_description'], job['days_old'])
        add_or_update_lead(lead['company_name'], {"status": "Scored", "interview_probability": match_data.get("interview_probability", 0)})

    # 3. Prioritization
    uncontacted_leads = get_all_uncontacted_scored_leads()
    prioritized_leads = mc.prioritize_opportunities(uncontacted_leads)
    
    logger.info(f"[Mission Control] Prioritized {len(prioritized_leads)} actionable opportunities.")
    
    results = []
    
    mc.max_daily_emails = 100
    
    for lead in prioritized_leads:
        from src.crm.database import get_daily_stats
        stats = get_daily_stats()
        if stats["emails_sent"] >= mc.max_daily_emails:
            logger.info(f"[Mission Control] Daily email limit reached ({stats['emails_sent']}/{mc.max_daily_emails}). Pausing.")
            break
            
        # Trigger Referral Engine for jobs that passed the threshold
        run_referral_engine(lead['company_name'], lead['job_title'], lead.get('job_description', ''))
        
        res = run_outreach_for_job(lead['job_id'], lead, mc)
        if res:
            results.append(res)
            
    mc.generate_daily_briefing()
    
    # Print the specific requirements for AFTER IMPLEMENTATION
    logger.info("\n==================================================")
    logger.info("TOP DISCOVERED OPPORTUNITIES (AFTER IMPLEMENTATION)")
    logger.info("==================================================")
    for i, lead in enumerate(prioritized_leads[:20]):
        logger.info(f"{i+1}. {lead['job_title']} @ {lead['company_name']} (Interview Prob: {lead.get('interview_probability', 0)}%)")
        
    logger.info("\n==================================================")
    logger.info("PROCESSED OUTCOMES")
    logger.info("==================================================")
    for r in results:
        logger.info(f"\nCompany: {r['company_name']}")
        logger.info(f"Match Score: {r['job_match_score']}")
        logger.info(f"Interview Prob: {r['interview_probability']}")
        logger.info(f"Selected Resume: {r['selected_resume']}")
        logger.info(f"Selected Project: {r['selected_project']}")
        logger.info(f"Selected Contact: {r['selected_contact']}")
        logger.info(f"Generated Email:\n{r['generated_email']}")

if __name__ == "__main__":
    run_batch_operations()
