from src.system.logger import setup_logger
logger = setup_logger('resume_engine')
from database import add_or_update_lead

def recommend_resume(domain: str, company_name: str) -> str:
    """
    Analyzes the domain and recommends which base resume to send.
    Options: AI Resume, Product Resume, Hybrid Resume
    """
    domain = (domain or "").lower()
    
    if "ai" in domain or "genai" in domain or "data" in domain or "analytics" in domain:
        family = "AI Resume"
    elif "saas" in domain or "enterprise" in domain or "cloud" in domain or "edtech" in domain:
        family = "Product Resume"
    else:
        family = "Hybrid Resume"
        
    add_or_update_lead(company_name, {"resume_family": family})
    logger.info(f"[{company_name}] Recommended Resume Family: {family}")
    return family

if __name__ == "__main__":
    recommend_resume("AI / GenAI", "OpenAI")
    recommend_resume("SaaS", "Salesforce")
    recommend_resume("Manufacturing", "Ford")
