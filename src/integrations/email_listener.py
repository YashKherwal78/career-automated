import imaplib
import email
from email.header import decode_header
import re
import os
from dotenv import load_dotenv

load_dotenv()

class EmailListener:
    def __init__(self):
        self.username = os.getenv("GMAIL_ADDRESS")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        self.imap_url = 'imap.gmail.com'
        
        if not self.username or not self.password:
            raise ValueError("GMAIL credentials missing for Email Automation.")

    def _connect(self):
        mail = imaplib.IMAP4_SSL(self.imap_url)
        mail.login(self.username, self.password)
        # READ-ONLY mode as requested
        mail.select("inbox", readonly=True)
        return mail

    def get_latest_otp(self, sender_domain: str, max_minutes_old: int = 5) -> str:
        """
        Connects in read-only mode and searches for a recent OTP from a specific domain.
        Returns the OTP string or None.
        """
        try:
            mail = self._connect()
            
            # Simple search by sender (in real-world, we'd use SINCE constraint based on date)
            status, messages = mail.search(None, f'FROM "{sender_domain}"')
            if status != 'OK':
                return None
                
            email_ids = messages[0].split()
            if not email_ids:
                return None
                
            # Get the latest email
            latest_id = email_ids[-1]
            status, msg_data = mail.fetch(latest_id, '(RFC822)')
            if status != 'OK':
                return None
                
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = ""
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body += part.get_payload(decode=True).decode()
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode()
                        except:
                            pass
                            
                    # Simple OTP regex: 6 digits usually
                    match = re.search(r'\b(\d{6})\b', body)
                    if match:
                        return match.group(1)
            
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"EmailListener Error: {e}")
            
        return None
        
    def get_magic_link(self, sender_domain: str) -> str:
        """
        Connects in read-only mode and searches for a magic verification link.
        """
        # Stub for magic link extraction logic
        return None
