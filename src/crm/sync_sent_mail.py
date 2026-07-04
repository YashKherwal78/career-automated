import os
import imaplib
import email
from email.utils import parseaddr
from email.header import decode_header
from dotenv import load_dotenv
from datetime import datetime

# Make sure imports resolve correctly when run from root
import sys
sys.path.append(os.getcwd())

from src.crm.database import init_db, upsert_contacted_email

def sync_sent_emails():
    load_dotenv()
    EMAIL = os.getenv("GMAIL_ADDRESS")
    APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

    if not EMAIL or not APP_PASSWORD:
        print("Error: GMAIL_ADDRESS and GMAIL_APP_PASSWORD not found in .env")
        return

    init_db()
    
    print(f"Connecting to IMAP as {EMAIL}...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, APP_PASSWORD)
    except Exception as e:
        print(f"Failed to connect to IMAP: {e}")
        return

    print("Selecting '[Gmail]/Sent Mail' folder...")
    status, messages = mail.select('"[Gmail]/Sent Mail"')
    if status != 'OK':
        print("Failed to select Sent Mail folder.")
        return

    # Search all emails
    status, response = mail.search(None, 'ALL')
    if status != 'OK':
        print("Failed to search emails.")
        return

    email_ids = response[0].split()
    total_emails = len(email_ids)
    print(f"Found {total_emails} sent emails. Processing in bulk chunks...")

    processed = 0
    extracted = 0
    
    chunk_size = 500
    for i in range(0, total_emails, chunk_size):
        chunk = email_ids[i:i+chunk_size]
        ids_str = b','.join(chunk).decode()
        
        status, msg_data = mail.fetch(ids_str, '(BODY[HEADER.FIELDS (TO CC DATE)])')
        if status != 'OK': continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Extract Date
                date_str = msg.get("Date", "")
                try:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    iso_date = dt.isoformat()
                except:
                    iso_date = datetime.now().isoformat()

                # Extract To & CC
                recipients = []
                for header in ["To", "Cc"]:
                    val = msg.get(header)
                    if val:
                        decoded = decode_header(val)
                        header_str = ""
                        for part, encoding in decoded:
                            if isinstance(part, bytes):
                                try:
                                    header_str += part.decode(encoding or 'utf-8', errors='ignore')
                                except:
                                    header_str += part.decode('latin-1', errors='ignore')
                            else:
                                header_str += part
                        
                        for addr in header_str.split(','):
                            name, email_addr = parseaddr(addr)
                            if email_addr:
                                recipients.append(email_addr.lower().strip())

                for r in recipients:
                    if r and r != EMAIL.lower():
                        upsert_contacted_email(r, iso_date)
                        extracted += 1
                        
        processed += len(chunk)
        print(f"Processed {processed}/{total_emails} emails...")

    mail.logout()
    print(f"Sync complete. Extracted {extracted} recipient instances across {total_emails} emails.")

if __name__ == "__main__":
    sync_sent_emails()
