"""SMTP email sender using Gmail with optional PDF attachment."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import streamlit as st

load_dotenv()


def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_name: str = "resume.pdf",
) -> None:
    """Send an email via Gmail SMTP with an optional PDF attachment.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        attachment_bytes: Raw bytes of the file to attach (optional).
        attachment_name: Filename shown in the email (default: resume.pdf).
    """
    gmail_user = st.secrets.get("GMAIL_USER") or os.getenv("GMAIL_USER")
    gmail_password = st.secrets.get("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        raise ValueError(
            "GMAIL_USER and GMAIL_APP_PASSWORD must be set in secrets.toml or your .env file."
        )

    msg = MIMEMultipart("mixed")
    msg["From"] = gmail_user
    msg["To"] = to
    msg["Subject"] = subject

    # Alternative part for plain + HTML body
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body, "plain"))
    html_body = (
        '<html><body style="font-family:Arial,sans-serif;font-size:15px;'
        'color:#222;line-height:1.7;max-width:640px;margin:auto;">'
        + "".join(
            f"<p>{line}</p>" for line in body.split("\n") if line.strip()
        )
        + "</body></html>"
    )
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # Attach PDF resume if provided
    if attachment_bytes:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment_name}"',
        )
        msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to, msg.as_string())
