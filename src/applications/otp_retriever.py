import re
import time
from datetime import datetime, timezone
from imap_tools import MailBox, AND
from src.config.config import Config

def retrieve_greenhouse_otp(application_start_time: datetime) -> dict:
    """
    Retrieves an OTP code and detailed forensics.
    Returns:
        {
            "code": str or None,
            "email_existed": bool,
            "extraction_failed_reason": str or None,
            "audit_logs": list,
            "delivery_latency_seconds": int or None
        }
    """
    from datetime import timedelta
    print(f"\n[OTP Retriever] === OTP EMAIL AUDIT MODE ===")
    print(f"[OTP Retriever] Requested At (Application Start): {application_start_time.isoformat()}")
    
    result = {
        "code": None,
        "email_existed": False,
        "extraction_failed_reason": None,
        "audit_logs": [],
        "delivery_latency_seconds": None
    }
    
    try:
        with MailBox('imap.gmail.com').login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD) as mailbox:
            # Fetch last 20 emails
            messages = list(mailbox.fetch(limit=20, reverse=True))
            
            for msg in messages:
                sender = msg.from_.lower()
                msg_date = msg.date
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                    
                start_time_aware = application_start_time
                if start_time_aware.tzinfo is None:
                    start_time_aware = start_time_aware.astimezone()
                
                # Only care about emails from the last 10 minutes for the dump
                if msg_date < start_time_aware - timedelta(minutes=10):
                    continue
                
                body = msg.text or msg.html
                body_preview = body[:50].replace('\n', ' ') + "..." if body else "Empty Body"
                
                log_entry = {
                    "sender": sender,
                    "subject": msg.subject,
                    "received_timestamp": msg_date.isoformat(),
                    "body_preview": body_preview
                }
                result["audit_logs"].append(log_entry)
                
                print(f"  -> Email: {sender} | Subj: {msg.subject} | Received: {msg_date.isoformat()}")
                
                # Check if it's the OTP email
                if ("greenhouse" in sender or "greenhouse.io" in sender) and msg_date >= start_time_aware:
                    result["email_existed"] = True
                    print(f"[OTP Retriever] >> MATCH: Greenhouse email detected! Analyzing body...")
                    
                    clean_body = re.sub(r'<[^>]+>', ' ', body)
                    clean_body = re.sub(r'\{[^\}]+\}', ' ', clean_body) # Remove CSS
                    
                    # Log Candidate Tokens
                    raw_words = re.findall(r'\b[A-Za-z0-9]{5,10}\b', clean_body)
                    candidates = re.findall(r'\b[A-Za-z0-9]{8}\b|\b[0-9]{6}\b', clean_body)
                    
                    print(f"[OTP Retriever] >> Candidate Tokens (8-char / 6-digit): {candidates}")
                    
                    best_code = None
                    for c in candidates:
                        if c.isalpha() and (c.islower() or c.istitle() or c.isupper()):
                            continue
                        best_code = c
                        break
                        
                    latency = (msg_date - start_time_aware).total_seconds()
                    print(f"[OTP Retriever] >> Delivery Latency: {latency} seconds")
                    result["delivery_latency_seconds"] = latency
                        
                    if best_code:
                        print(f"[OTP Retriever] >> SUCCESS: Extracted '{best_code}'")
                        result["code"] = best_code
                        return result
                    else:
                        reason = f"Found {len(candidates)} candidates, but all failed strict validation (likely english words or wrong format)."
                        print(f"[OTP Retriever] >> EXTRACTION FAILED: {reason}")
                        print(f"[OTP Retriever] >> Raw words in body (5-10 chars): {raw_words}")
                        result["extraction_failed_reason"] = reason
                        
    except Exception as e:
        print(f"[OTP Retriever] IMAP Error: {e}")
        result["extraction_failed_reason"] = f"IMAP Error: {e}"
        
    print(f"[OTP Retriever] === END AUDIT ===\n")
    return result
