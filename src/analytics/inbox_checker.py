import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
from database import get_connection, update_status

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_ADDRESS")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
IMAP_SERVER = "imap.gmail.com"

def check_inbox_for_replies():
    print("Checking inbox for replies...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Search for all unseen emails
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            print("No new unseen messages.")
            mail.logout()
            return

        for num in messages[0].split():
            status, data = mail.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    sender = msg.get("From", "")
                    # Extract email from sender string (e.g., "Name <email@example.com>")
                    if "<" in sender and ">" in sender:
                        sender_email = sender.split("<")[1].split(">")[0].strip().lower()
                    else:
                        sender_email = sender.strip().lower()

                    print(f"Found unseen email from: {sender_email}")
                    
                    # Check if this email matches anyone in our database
                    conn = get_connection()
                    cursor = conn.cursor()
                    # Check HR email
                    cursor.execute("SELECT company_name, status FROM leads WHERE LOWER(hr_email) = ?", (sender_email,))
                    row = cursor.fetchone()
                    if row:
                        company_name, current_status = row
                        print(f"Match found for HR of {company_name}!")
                        if current_status not in ["HR Replied", "Interview Scheduled"]:
                            update_status(company_name, "HR Replied", "hr_contact_date") # Repurpose date field or add new one, we will just use update_status
                            print(f"Updated status for {company_name} to HR Replied.")
                    
                    # Check Founder email
                    cursor.execute("SELECT company_name, status FROM leads WHERE LOWER(founder_email) = ?", (sender_email,))
                    row = cursor.fetchone()
                    if row:
                        company_name, current_status = row
                        print(f"Match found for Founder of {company_name}!")
                        if current_status not in ["Founder Replied", "Interview Scheduled"]:
                            update_status(company_name, "Founder Replied", "founder_contact_date")
                            print(f"Updated status for {company_name} to Founder Replied.")

                    conn.close()

        mail.logout()
        print("Inbox check complete.")

    except Exception as e:
        print(f"IMAP Error: {e}")

if __name__ == "__main__":
    check_inbox_for_replies()
