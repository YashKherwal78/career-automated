import re
from datetime import datetime, timezone, timedelta
from imap_tools import MailBox, AND
from src.config.config import Config
import sqlite3

class EmailConfirmationChecker:
    @staticmethod
    def check_for_confirmation(company_name: str, job_title: str, since_minutes: int = 15) -> bool:
        """
        Checks Gmail for a recent confirmation email from an ATS for the given company and role.
        """
        try:
            with MailBox('imap.gmail.com').login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD) as mailbox:
                start_time = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
                
                messages = list(mailbox.fetch(AND(seen=False), limit=20, reverse=True))
                
                for msg in messages:
                    sender = msg.from_.lower()
                    subject = msg.subject.lower()
                    body = (msg.text or msg.html).lower()
                    
                    # Ensure msg.date is timezone-aware
                    msg_date = msg.date
                    if msg_date.tzinfo is None:
                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                        
                    if msg_date < start_time:
                        continue
                        
                    # Check if it's from a known ATS or the company itself
                    ats_keywords = ["greenhouse", "stripe", "lever", "workday", "ashby", "smartrecruiters", "application", "careers", company_name.lower()]
                    if not any(kw in sender for kw in ats_keywords):
                        continue
                        
                    # Check for confirmation phrases in subject or body
                    success_phrases = [
                        "thank you for applying",
                        "we've received your application",
                        "your application has been received",
                        "application submitted",
                        "successfully applied"
                    ]
                    
                    has_success_phrase = any(phrase in subject or phrase in body for phrase in success_phrases)
                    
                    # Fuzz match company and role
                    # Sometimes role titles are slightly different, so we check if parts match
                    role_parts = [p for p in job_title.lower().split() if len(p) > 3]
                    role_match = any(part in subject or part in body for part in role_parts) if role_parts else True
                    
                    company_match = company_name.lower() in sender or company_name.lower() in subject or company_name.lower() in body
                    
                    if has_success_phrase and company_match and role_match:
                        print(f"[EmailConfirmationChecker] Found confirmation email from {sender}: {msg.subject}")
                        return True
        except Exception as e:
            print(f"[EmailConfirmationChecker] Error checking emails: {e}")
            
        return False
