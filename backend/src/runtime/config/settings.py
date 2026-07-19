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
    AUTH_DATABASE_URL: str = os.getenv("AUTH_DATABASE_URL", "").strip("'\"")
    OPERATIONAL_DATABASE_URL: str = os.getenv("OPERATIONAL_DATABASE_URL", "").strip("'\"")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "").strip("'\"")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip("'\"")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip("'\"")
    
    # Cloudflare R2
    R2_BUCKET: str = os.getenv("CLOUDFLARE_R2_BUCKET", "careerautomated-assets").strip("'\"")
    R2_ENDPOINT: str = os.getenv("CLOUDFLARE_R2_ENDPOINT", "").strip("'\"")
    R2_ACCESS_KEY_ID: str = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "").strip("'\"")
    R2_SECRET_ACCESS_KEY: str = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "").strip("'\"")
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip("'\"")
    GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "").strip("'\"")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "").strip("'\"")
    
    @classmethod
    def use_postgres(cls, db_url: str) -> bool:
        return db_url.startswith("postgresql://") or db_url.startswith("postgres://")
    
    @classmethod
    def validate(cls):
        """Validate critical environment variables are present."""
        missing = []
        if not cls.AUTH_DATABASE_URL: missing.append("AUTH_DATABASE_URL")
        if not cls.OPERATIONAL_DATABASE_URL: missing.append("OPERATIONAL_DATABASE_URL")
        if not cls.REDIS_URL: missing.append("REDIS_URL")
        if not cls.R2_ENDPOINT: missing.append("CLOUDFLARE_R2_ENDPOINT")
        if not cls.R2_ACCESS_KEY_ID: missing.append("CLOUDFLARE_R2_ACCESS_KEY_ID")
        if not cls.R2_SECRET_ACCESS_KEY: missing.append("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
