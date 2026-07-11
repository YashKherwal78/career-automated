import os
import sys

# Ensure absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import smtplib
import imaplib
from src.system.logger import setup_logger

logger = setup_logger("HealthCheck")

class HealthCheckFailed(Exception):
    pass

def check_env_vars():
    required_vars = ["GROQ_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing essential environment variables: {missing}")
        return False
    return True

def check_directories():
    required_dirs = ["logs", "data", "data/reports"]
    missing = [d for d in required_dirs if not os.path.exists(d)]
    if missing:
        logger.error(f"Missing required directories: {missing}")
        return False
    return True

def check_files():
    required_files = [
        ".env", 
        "data/crm.db",
        "yash_resume_base_v2.tex",
        "yash_resume_aiproduct.pdf"
    ]
    missing = [f for f in required_files if not os.path.exists(f)]
    if missing:
        logger.error(f"Missing essential files: {missing}")
        return False
    return True

def check_playwright():
    try:
        import playwright
        return True
    except ImportError:
        logger.error("Playwright module is not installed.")
        return False

def check_resume():
    return True # Handled in check_files now

def check_smtp_imap():
    email = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not email or not password:
        return False
        
    try:
        # Check SMTP
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(email, password)
        server.quit()
        
        # Check IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email, password)
        mail.logout()
        return True
    except Exception as e:
        logger.error(f"SMTP/IMAP Authentication failed: {e}")
        return False

def run_health_check():
    logger.info("Starting System Health Check...")
    
    checks = {
        "Environment Variables": check_env_vars,
        "Required Directories": check_directories,
        "Required Assets": check_files,
        "Playwright Installation": check_playwright,
        "Email Infrastructure (SMTP/IMAP)": check_smtp_imap
    }
    
    all_passed = True
    logger.info("\n--- System Status ---")
    for name, func in checks.items():
        try:
            status = func()
            if status:
                logger.info(f"{name.ljust(35)} PASS")
            else:
                logger.info(f"{name.ljust(35)} FAIL")
                all_passed = False
        except Exception as e:
            logger.error(f"Health check '{name}' threw an exception: {e}")
            logger.info(f"{name.ljust(35)} ERROR")
            all_passed = False
            
    logger.info("---------------------\n")
    if not all_passed:
        logger.critical("Health check failed. Pipeline cannot start.")
        sys.exit(1)
        
    logger.info("System Health Check passed. All systems GO.")

if __name__ == "__main__":
    run_health_check()
