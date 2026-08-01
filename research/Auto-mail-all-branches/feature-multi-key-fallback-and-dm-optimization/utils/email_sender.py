"""SMTP email sender using Gmail — plain text with optional PDF attachment."""
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
    gmail_user_override: str | None = None,
    gmail_pass_override: str | None = None,
) -> None:
    """Send a plain-text email via Gmail SMTP with an optional PDF attachment.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        attachment_bytes: Raw bytes of the file to attach (optional).
        attachment_name: Filename shown in the email (default: resume.pdf).
        gmail_user_override: Use this Gmail address instead of secrets/env.
        gmail_pass_override: Use this app password instead of secrets/env.
    """
    if gmail_user_override:
        gmail_user = gmail_user_override
        gmail_password = gmail_pass_override
    else:
        try:
            gmail_user = (
                st.secrets.get("PRIYA_GMAIL_USER")
                or st.secrets.get("GMAIL_USER")
                or os.getenv("GMAIL_USER")
            )
            gmail_password = (
                st.secrets.get("PRIYA_GMAIL_APP_PASSWORD")
                or st.secrets.get("GMAIL_APP_PASSWORD")
                or os.getenv("GMAIL_APP_PASSWORD")
            )
        except Exception:
            gmail_user = os.getenv("GMAIL_USER")
            gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        raise ValueError(
            "Gmail credentials are not configured. "
            "Add GMAIL_USER and GMAIL_APP_PASSWORD to secrets.toml."
        )

    import re
    def text_to_html(text: str) -> str:
        html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Convert plain URLs to clickable hyperlinks (before newline conversion)
        html = re.sub(
            r'(?<!href=["\'])(https?://[^\s<>"]+)',
            r'<a href="\1" style="color:#2563eb;">\1</a>',
            html,
        )
        html = html.replace('\n', '<br>')
        return f"<html><body><div style='font-family: Arial, sans-serif; font-size: 14px;'>{html}</div></body></html>"

    html_body = text_to_html(body)

    if attachment_bytes:
        msg = MIMEMultipart("mixed")
        msg["From"] = gmail_user
        msg["To"] = to
        msg["Subject"] = subject
        
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment_name}"',
        )
        msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg["From"] = gmail_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to, msg.as_string())
