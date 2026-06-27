import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    GROQ_KEYS = [
        os.getenv("GROQ_API_KEY"),  # legacy support
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3")
    ]
    GROQ_KEYS = [k for k in GROQ_KEYS if k]
    GROQ_API_KEY = GROQ_KEYS[0] if GROQ_KEYS else ""
    GETPROSPECT_API_KEY = os.getenv("GETPROSPECT_API_KEY")
    HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
    
    DATA_DIR = BASE_DIR / "data"
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "crm.db"))
    
    # Discovery Budgets
    WELLFOUND_MAX_REQUESTS_PER_RUN = 50
    GREENHOUSE_MAX_API_CALLS_PER_RUN = 100
    GOOGLE_SEARCH_MAX_QUERIES_PER_RUN = 20
    SERPER_DAILY_CREDIT_LIMIT = 100

    OUTREACH_TRACE_MODE = False

    APIFY_KEYS = [
        os.getenv(f"APIFY_KEY_{i}") for i in range(1, 9) if os.getenv(f"APIFY_KEY_{i}")
    ]
    
    APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "hKByXkMQaC5Qt9UMN")
    MAX_APIFY_RUNS_PER_DAY = int(os.getenv("MAX_APIFY_RUNS_PER_DAY", "10"))
    MAX_APIFY_DISCOVERY_RUNS_PER_DAY = int(os.getenv("MAX_APIFY_DISCOVERY_RUNS_PER_DAY", "2"))
    MAX_APIFY_RUNS_PER_JOB = int(os.getenv("MAX_APIFY_RUNS_PER_JOB", "1"))
    
    MAX_APIFY_MONTHLY_BUDGET = float(os.getenv("MAX_APIFY_MONTHLY_BUDGET", "40.00"))
    APIFY_SOFT_LIMIT = 30.00
    APIFY_HARD_LIMIT = 35.00
    
    APIFY_PROVIDERS = [
        {
            "name": "fantastic_career_site",
            "actor_id": "fantastic-jobs/career-site-job-listing-api",
            "enabled": True,
            "priority": 1
        },
        {
            "name": "fantastic_greenhouse",
            "actor_id": "fantastic-jobs/greenhouse-jobs-api",
            "enabled": True,
            "priority": 2
        }
    ]
    
    APIFY_NORMALIZATION = {
        "title": ["title", "jobTitle", "position", "role"],
        "company": ["company", "companyName", "employer"],
        "location": ["location", "jobLocation"],
        "url": ["url", "jobUrl", "applyUrl", "absolute_url"],
        "ats": ["ats", "provider", "board"],
        "posted_date": ["postedAt", "createdAt", "publishedAt", "updated_at"]
    }
    
    JOB_MATCH_THRESHOLD = int(os.getenv("JOB_MATCH_THRESHOLD", "75"))
    CANDIDATE_STRATEGY = os.getenv("CANDIDATE_STRATEGY", "BALANCED")
    
    # Match Engine V1.4 Penalties
    PENALTY_SENIOR_ROLE = int(os.getenv("PENALTY_SENIOR_ROLE", "30"))
    PENALTY_EXPERIENCE = int(os.getenv("PENALTY_EXPERIENCE", "30"))
    PENALTY_DEGREE = int(os.getenv("PENALTY_DEGREE", "20"))
    PENALTY_ENTERPRISE = int(os.getenv("PENALTY_ENTERPRISE", "15"))
    PENALTY_DOMAIN = int(os.getenv("PENALTY_DOMAIN", "15"))
    
    WELLFOUND_DAILY_LIMIT = int(os.getenv("WELLFOUND_DAILY_LIMIT", "3"))
    
    APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
    EXPLORIUM_API_KEY = os.getenv("EXPLORIUM_API_KEY")

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
        if not cls.APIFY_KEYS: missing.append("APIFY_KEY_1")
        if missing: raise ValueError(f"Missing required env vars: {missing}")

if __name__ == "__main__":
    Config.validate()
