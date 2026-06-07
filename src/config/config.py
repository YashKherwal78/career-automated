import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEY_BACKUP = os.getenv("GROQ_API_KEY_BACKUP", "")
    GETPROSPECT_API_KEY = os.getenv("GETPROSPECT_API_KEY")
    HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
    
    DATA_DIR = BASE_DIR / "data"
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "crm.db"))

    APIFY_API_KEY = os.getenv("APIFY_API_KEY")
    JOB_MATCH_THRESHOLD = int(os.getenv("JOB_MATCH_THRESHOLD", "75"))
    MAX_DAILY_EMAILS = int(os.getenv("MAX_DAILY_EMAILS", "50"))
    MAX_BOUNCE_RATE = float(os.getenv("MAX_BOUNCE_RATE", "0.10"))
    MIN_INTERVIEW_PROBABILITY = int(os.getenv("MIN_INTERVIEW_PROBABILITY", "70"))
    CONTACT_CONFIDENCE_THRESHOLD = float(os.getenv("CONTACT_CONFIDENCE_THRESHOLD", "0.7"))

    @classmethod
    def validate(cls):
        missing = []
        if not cls.GROQ_API_KEY: missing.append("GROQ_API_KEY")
        if not cls.GMAIL_ADDRESS: missing.append("GMAIL_ADDRESS")
        if not cls.GMAIL_APP_PASSWORD: missing.append("GMAIL_APP_PASSWORD")
        if not cls.APIFY_API_KEY: missing.append("APIFY_API_KEY")
        if missing: raise ValueError(f"Missing required env vars: {missing}")

if __name__ == "__main__":
    Config.validate()
