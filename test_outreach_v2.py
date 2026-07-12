import os
import time
from src.config.config import Config
from src.outreach.engine import OutreachEngine
from src.intelligence.intelligence import run_intelligence_engine
from src.intelligence.project_selector import ProjectSelector
from src.outreach.critic import EmailCritic
from src.outreach.email_client import ResumeAttachmentError

def test_v2_pipeline():
    print("\n--- OUTREACH V2 PIPELINE TEST ---\n")
    engine = OutreachEngine(dry_run=False) # We want to ACTUALLY send it
    critic = EmailCritic()
    
    email_val = "yash.kherwal78@gmail.com" # Send to Yash
    name_val = "Yash Test"
    company_val = "Meesho"
    role_val = "Software Engineer"
    notes_val = "Testing the V2 Architecture"
    
    print(f"Target: {company_val}")
    
    # 1. Company Intelligence
    print("1. Running Company Intelligence...")
    intel = run_intelligence_engine(engine.client, company_val)
    domain = intel.get("domain", "Other")
    print(f"   Domain: {domain}")
    
    # 2. Project Selection
    print("2. Running Project Selection...")
    project = ProjectSelector.select(domain)
    print(f"   Selected Project: {project}")
    
    # 3. Email Generation & Critic Loop
    print("3. Generating Email & Passing to Critic...")
    subject, body = "", ""
    critic_passed = False
    critic_result = {}
    for attempt in range(3):
        subject, body = engine.generate_email(name_val, company_val, role_val, notes_val, domain, project)
        critic_result = critic.evaluate(body, company_val, project)
        if critic_result.get("status") == "PASS":
            critic_passed = True
            print("   Critic: PASS")
            break
        else:
            print(f"   Critic Rejected Attempt {attempt+1}: {critic_result.get('reason')}")
            
    if not critic_passed:
        print("   FAILED to pass Email Critic.")
        return
        
    print(f"\n--- APPROVED EMAIL DRAFT ---\nSubject: {subject}\n\n{body}\n----------------------------\n")
        
    # 4. Resume Attachment (Fixed Outreach Resume)
    print("4. Attaching Fixed Outreach Resume...")
    resume_path = str(Config.DATA_DIR / "yash_outreach_resume.pdf")
    if not os.path.exists(resume_path):
        resume_path = str(Config.DATA_DIR / "yash_resume_sde.pdf")
        if not os.path.exists(resume_path):
            resume_path = str(Config.DATA_DIR / "yash_resume_aiml.pdf")
    
    print(f"   Generated Resume Path: {resume_path}")
    
    # 5. Attachment Validation & Send
    print("5. Validating Attachment & Sending...")
    success = False
    attachment_status = "OK"
    try:
        success = engine.email_client.send_email(email_val, subject, body, resume_path=resume_path, dry_run=False)
        print("   SMTP SEND SUCCESS" if success else "   SMTP SEND FAILED")
    except (ResumeAttachmentError, ValueError) as e:
        print(f"   Attachment Validation Failed: {e}")
        attachment_status = f"FAILED: {e}"
        success = False
        
    print(f"\n--- TRACE LOG ---")
    print(f"Company: {company_val}")
    print(f"Domain: {domain}")
    print(f"Selected Project: {project}")
    print(f"Critic Result: PASS")
    print(f"Resume Path: {resume_path}")
    print(f"Attachment Status: {attachment_status}")
    print(f"Send Status: {'SENT' if success else 'FAILED'}")
    print(f"-----------------\n")

if __name__ == "__main__":
    test_v2_pipeline()
