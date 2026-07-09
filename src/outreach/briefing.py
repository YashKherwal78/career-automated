from src.system.logger import setup_logger
logger = setup_logger('briefing')
import sqlite3
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.config.config import Config
from src.crm.database import DB_PATH

def generate_and_send_briefing():
    logger.info("\n[Briefing] Generating Daily Executive Briefing...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Discovery Stats
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE date(posting_date) = date('now')")
    jobs_found = cursor.fetchone()[0]
    
    # Outreach Stats
    cursor.execute("SELECT COUNT(*) FROM leads WHERE hr_contacted = 1 AND date(hr_contact_date) = date('now')")
    emails_sent = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE bounced = 1")
    bounces = cursor.fetchone()[0]
    
    # Response Stats
    cursor.execute("SELECT COUNT(*) FROM leads WHERE hr_replied = 1")
    replies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE interview_scheduled = 1")
    interviews = cursor.fetchone()[0]
    
    # Top Jobs
    cursor.execute("SELECT company_name, job_title, job_url, interview_probability FROM leads WHERE status = 'Scored' OR status = 'New' ORDER BY interview_probability DESC LIMIT 5")
    top_jobs = cursor.fetchall()
    
    # Top Referrals
    cursor.execute("SELECT company, job_title, contact_name, referral_score, ranking_reason FROM referral_contacts ORDER BY referral_score DESC LIMIT 5")
    top_referrals = cursor.fetchall()
    
    conn.close()
    
    bounce_rate = (bounces / emails_sent * 100) if emails_sent > 0 else 0.0
    
    html = f"""
    <html>
    <body>
        <h2>Recruiting Intelligence - Daily Briefing</h2>
        
        <h3>Discovery</h3>
        <ul>
            <li>Jobs Found Today: <b>{jobs_found}</b></li>
        </ul>
        
        <h3>Outreach</h3>
        <ul>
            <li>Emails Sent Today: <b>{emails_sent}</b></li>
            <li>Total Bounces: <b>{bounces}</b> ({bounce_rate:.1f}%)</li>
        </ul>
        
        <h3>Responses</h3>
        <ul>
            <li>Total Replies: <b>{replies}</b></li>
            <li>Interview Requests: <b>{interviews}</b></li>
        </ul>
        
        <h3>Top Recommended Jobs to Apply For</h3>
        <ul>
    """
    
    for job in top_jobs:
        html += f"<li><b>{job['company_name']}</b> - {job['job_title']} (Interview Prob: {job['interview_probability']}%)<br><a href='{job['job_url']}'>Link</a></li>"
        
    html += """
        </ul>
        
        <h3>Top Referral Opportunities</h3>
        <ul>
    """
    
    for ref in top_referrals:
        html += f"<li><b>{ref['contact_name']}</b> @ {ref['company']} (Score: {ref['referral_score']})<br><i>{ref['ranking_reason']}</i></li>"
        
    html += """
        </ul>
    </body>
    </html>
    """
    
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"Daily Briefing - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = Config.GMAIL_ADDRESS
    msg['To'] = Config.GMAIL_ADDRESS
    
    msg.attach(MIMEText(html, "html"))
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info("✅ Briefing sent to", Config.GMAIL_ADDRESS)
    except Exception as e:
        logger.info(f"❌ Failed to send briefing: {e}")

if __name__ == "__main__":
    generate_and_send_briefing()
