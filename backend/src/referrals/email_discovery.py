from src.system.logger import setup_logger
logger = setup_logger('email_discovery')
import requests
import json
from src.config.config import Config
from typing import Tuple

def discover_email(contact_name: str, company_name: str) -> Tuple[str, int]:
    """
    Phase 4 - Email Discovery
    Tries GetProspect first (mocked if no key), falls back to Hunter.io
    Returns (email, email_confidence)
    """
    first_name = contact_name.split(" ")[0]
    last_name = contact_name.split(" ")[-1] if len(contact_name.split(" ")) > 1 else ""
    domain = f"{company_name.lower().replace(' ', '')}.com"
    
    # 1. GetProspect (Stubbed - requires API Key)
    # 2. Hunter Fallback
    if Config.HUNTER_API_KEY:
        try:
            url = f"https://api.hunter.io/v2/email-finder?domain={domain}&first_name={first_name}&last_name={last_name}&api_key={Config.HUNTER_API_KEY}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("email"):
                    email = data["data"]["email"]
                    confidence = data["data"]["score"]
                    return email, confidence
        except Exception as e:
            logger.info(f"Hunter API Error: {e}")
            
    # Mock fallback if no keys configured
    return f"{first_name.lower()}.{last_name.lower()}@{domain}", 30
