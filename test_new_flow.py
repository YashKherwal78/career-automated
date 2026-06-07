import os
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from database import init_db, add_or_update_lead, get_lead
from intelligence import run_intelligence_engine
from enrichment import enrich_company
from resume_engine import recommend_resume
from prompts import HR_SYSTEM_PROMPT, FOUNDER_SYSTEM_PROMPT
from ddgs import DDGS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import Config

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = Config.GMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach Resume
    try:
        with open("Resume_aiml.pdf", "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename="Yash_Kherwal_Resume.pdf")
            msg.attach(attach)
    except Exception as e:
        print(f"Could not attach resume: {e}")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Successfully sent email to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")

SUBJECT_VARIANTS = {
    "AI / GenAI": ["IIT Roorkee Student | AI Engineering Opportunities", "AI Engineer Intern Candidate | IIT Roorkee"],
    "Enterprise Software": ["IIT Roorkee Student | Software Engineering Opportunities", "Exploring Software Engineering Roles at {Company}"],
    "Other": ["IIT Roorkee Student | Software Engineering Opportunities"]
}

def get_company_context(company_name: str) -> str:
    query = f"{company_name} company what they do software products"
    results = DDGS().text(query, max_results=3)
    if not results: return "No web context found."
    return " ".join([res["body"] for res in results])

def orchestrate_10_phase_agent(company_name: str):
    print(f"=== RECRUITING INTELLIGENCE PLATFORM: Processing {company_name} ===")
    
    # Phase 1, 2, 3: Intelligence
    print("\n[Phase 1-3] Intelligence Engine...")
    metadata = run_intelligence_engine(groq_client, company_name)
    domain = metadata.get("domain", "Other")
    
    # Phase 1.5: Enrichment Layer
    print("\n[Enrichment Layer] Running Contact Enrichment...")
    enrichment_data = enrich_company(company_name)
    metadata.update(enrichment_data)
    
    # Phase 1.6: Resume Recommendation Engine
    print("\n[Resume Engine] Recommending Resume Family...")
    metadata["resume_family"] = recommend_resume(domain, company_name)
    
    # Phase 10: Subject Testing
    variants = SUBJECT_VARIANTS.get(domain, SUBJECT_VARIANTS["Other"])
    metadata["subject_variant"] = random.choice(variants).replace("{Company}", company_name)
    
    # Save to CRM
    add_or_update_lead(company_name, metadata)
    
    # Web search context
    context = get_company_context(company_name)
    
    # Phase 4 & 5: HR Email
    print("\n[Phases 4-5] Generating Phase 1 HR Outreach Email...")
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": HR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Target Company: {company_name}\nCompany Context: {context}\nForced Subject: {metadata['subject_variant']}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    email_data = json.loads(response.choices[0].message.content)
    # Extract lead data to get the HR email
    lead = get_lead(company_name)
    hr_email = lead.get("hr_email") if lead else None
    
    print(f"Subject: {email_data.get('subject', metadata['subject_variant'])}\n")
    print(email_data.get('body', ''))
    
    if hr_email:
        send_email(hr_email, email_data.get('subject', metadata['subject_variant']), email_data.get('body', ''))
    else:
        print("❌ No HR email found to send to.")
        
    add_or_update_lead(company_name, {"status": "HR Contacted", "hr_contacted": 1, "hr_contact_date": datetime.now().isoformat()})

    score = metadata.get("priority_score", 0)
    print(f"\n[Phase 6 & 7] Evaluating Founder Escalation Strategy... (Score: {score})")
    if score >= 7 and metadata.get("founder_email"):
        print(f"Proceeding to Founder Email.")
        founder_name = metadata.get("founder_name", "Founder")
        
        prompt = FOUNDER_SYSTEM_PROMPT.replace("{Founder Name}", founder_name)
        response2 = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Target Company: {company_name}\nCompany Context: {context}\nDomain: {domain}"}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        founder_data = json.loads(response2.choices[0].message.content)
        print(f"\nSubject: {founder_data.get('subject', 'Quick question')}\n")
        print(founder_data.get('body', ''))
        
        if founder_data and metadata.get("founder_email"):
            send_email(metadata["founder_email"], founder_data.get('subject', 'Quick question'), founder_data.get('body', ''))
            
        add_or_update_lead(company_name, {"status": "Founder Contacted", "founder_contacted": 1, "founder_contact_date": datetime.now().isoformat()})
    else:
        reason = "Score < 7" if score < 7 else "No Founder Email found"
        print(f"Escalation aborted: {reason}. Outreach limited to HR.")

if __name__ == "__main__":
    orchestrate_10_phase_agent("Sailotech")
