import json
from typing import Dict
from src.config.config import Config

def scrape_profile(linkedin_url: str) -> Dict:
    """
    Phase 2 - Profile Intelligence
    Uses Apify LinkedIn Profile Scraper.
    For V0.1 MVP, we will mock the return payload so we don't consume Apify credits,
    but the schema matches what Apify would return.
    """
    if not linkedin_url:
        return {}
        
    print(f"Scraping profile: {linkedin_url}")
    
    # Mocking Apify Actor output for V0.1
    # If the URL contains an IIT hint, we inject IIT Roorkee for testing
    education_str = "B.Tech Computer Science"
    if "iit" in linkedin_url.lower() or "sharma" in linkedin_url.lower():
        education_str = "B.Tech Computer Science, Indian Institute of Technology Roorkee"
        
    mock_payload = {
        "headline": "Engineering Leader | Building Scalable Systems",
        "education": education_str,
        "experience": "Senior Engineer at Current Company",
        "skills": "Python, Machine Learning, System Design",
        "profile_confidence": 95
    }
    
    return mock_payload
