import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[4]
load_dotenv(BASE_DIR / ".env")

class Settings:
    # Environment
    APP_ENV: str = os.getenv("APP_ENV", "production")
    ENABLE_LOCAL_FALLBACKS: bool = os.getenv("ENABLE_LOCAL_FALLBACKS", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Cloudflare R2
    R2_BUCKET: str = os.getenv("CLOUDFLARE_R2_BUCKET", "careerautomated-assets")
    R2_ENDPOINT: str = os.getenv("CLOUDFLARE_R2_ENDPOINT", "")
    R2_ACCESS_KEY_ID: str = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    
    @classmethod
    def validate(cls):
        """Validate critical environment variables are present."""
        missing = []
        if not cls.DATABASE_URL: missing.append("DATABASE_URL")
        if not cls.REDIS_URL: missing.append("REDIS_URL")
        if not cls.R2_ENDPOINT: missing.append("CLOUDFLARE_R2_ENDPOINT")
        if not cls.R2_ACCESS_KEY_ID: missing.append("CLOUDFLARE_R2_ACCESS_KEY_ID")
        if not cls.R2_SECRET_ACCESS_KEY: missing.append("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
