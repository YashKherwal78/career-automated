import json
from imap_tools import MailBox, AND
from groq import Groq
from src.config.config import Config
from src.crm.database import get_lead_by_hr_email, add_or_update_lead
from src.crm.state_machine import CRMState, transition_state

def classify_reply(groq_client: Groq, email_body: str) -> dict:
    prompt = f"""
    You are an expert HR response classifier.
    Read the following email reply from an HR recruiter or founder.
    
    EMAIL:
    {email_body}
    
    Classify the response into EXACTLY ONE of these categories:
    - INTERVIEW REQUEST: They want to schedule a call or interview.
    - POSITIVE INTEREST: They are interested but didn't explicitly ask for a call yet.
    - REFERRAL: They are passing the candidate to someone else.
    - REJECTION: They are passing on the candidate.
    - AUTO REPLY: Out of office or automated response.
    - BOUNCE: Delivery failed.
    
    Return ONLY valid JSON:
    {{
        "classification": "REJECTION",
        "reason": "Explicitly stated they are not hiring interns right now."
    }}
    """
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Classifier error: {e}")
        return {"classification": "UNKNOWN", "reason": str(e)}

def monitor_inbox():
    print("\n[Inbox Monitor] Connecting to Gmail via IMAP...")
    try:
        client = Groq(api_key=Config.GROQ_API_KEY)
        
        with MailBox('imap.gmail.com').login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD) as mailbox:
            # Fetch unread emails
            for msg in mailbox.fetch(AND(seen=False)):
                sender = msg.from_
                body = msg.text or msg.html
                print(f"Unread email from: {sender}")
                
                # Look up sender in CRM
                lead = get_lead_by_hr_email(sender)
                if not lead:
                    print(f"Sender {sender} not found in CRM. Skipping.")
                    continue
                    
                company_name = lead["company_name"]
                
                # Classify
                classification_data = classify_reply(client, body)
                cls = classification_data.get("classification", "UNKNOWN")
                
                print(f"Classified {company_name} reply as: {cls}")
                
                # Update CRM
                update_data = {
                    "hr_replied": 1,
                    "reply_body": body
                }
                
                if cls == "INTERVIEW REQUEST":
                    transition_state(company_name, CRMState.INTERVIEW_SCHEDULED)
                    update_data["interview_scheduled"] = 1
                elif cls == "BOUNCE":
                    transition_state(company_name, CRMState.HARD_BOUNCE)
                    update_data["bounced"] = 1
                elif cls == "AUTO_REPLY":
                    # Don't transition state, just mark as contacted
                    pass
                else:
                    transition_state(company_name, CRMState.HR_REPLIED)
                    
                add_or_update_lead(company_name, update_data)
                
    except Exception as e:
        print(f"Inbox Monitor failed: {e}")

if __name__ == "__main__":
    monitor_inbox()
