from src.system.logger import setup_logger
logger = setup_logger('email_client')
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config.config import Config

import os
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

class ResumeAttachmentError(Exception):
    pass


def retry_if_transient_error(exception):
    import smtplib
    if isinstance(exception, smtplib.SMTPAuthenticationError):
        return False
    error_str = str(exception).lower()
    if any(x in error_str for x in ["auth", "credentials", "login"]):
        return False
    return True

class EmailClient:

    def __init__(self):
        self.email_address = Config.GMAIL_ADDRESS
        self.password = Config.GMAIL_APP_PASSWORD
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.imap_server = "imap.gmail.com"
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=15), retry=tenacity.retry_if_exception(retry_if_transient_error))
    def send_email(self, to_email: str, subject: str, body: str, resume_path: str = None, dry_run: bool = False) -> bool:
        if resume_path:
            if not os.path.exists(resume_path):
                raise ResumeAttachmentError(f"Resume path does not exist: {resume_path}")
            if os.path.getsize(resume_path) == 0:
                raise ResumeAttachmentError(f"Resume file is empty: {resume_path}")
                
        banned_placeholders = ["[recruiter name]", "[name]", "{name}", "{recruiter}", "[first name]", "{first name}", "hi ,", "hello ,", "dear ,"]
        body_lower = body.lower()
        for ph in banned_placeholders:
            if ph in body_lower:
                raise ValueError(f"Unresolved placeholder detected before send: {ph}")
                
        if dry_run:
            logger.info(f"[DRY RUN] Would send to: {to_email} | Subject: {subject} | Attachment: {resume_path}")
            return True
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            if resume_path:
                from email.mime.application import MIMEApplication
                with open(resume_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(resume_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(resume_path)}"'
                msg.attach(part)
                
                # Check MIME payload
                if len(msg.get_payload()) < 2:
                    raise ResumeAttachmentError("MIME payload does not contain the attachment.")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.email_address, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.info(f"Failed to send email to {to_email}: {e}")
            raise  # Let tenacity retry it
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=15), retry=tenacity.retry_if_exception(retry_if_transient_error))
    def check_replies(self) -> list:
        replies = []
        try:
            # IMAP timeout handling is implicit in python 3.9+, passing it directly
            import socket
            socket.setdefaulttimeout(30)
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")
            
            # Fetch unread emails
            _, search_data = mail.search(None, 'UNSEEN')
            
            for num in search_data[0].split():
                _, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                from_addr = email.utils.parseaddr(msg['From'])[1]
                
                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                    
                replies.append({
                    "from": from_addr,
                    "subject": msg['Subject'],
                    "body": body
                })
                
            mail.logout()
            return replies
        except Exception as e:
            logger.info(f"Error checking replies: {e}")
            raise  # Let tenacity retry it
