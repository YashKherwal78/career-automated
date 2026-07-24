import re
from typing import Dict, Any

def extract_experience(text: str) -> Dict[str, Any]:
    """Extracts minimum/maximum years of experience and checks if it is fresher friendly."""
    exp = {"experience_min": None, "experience_max": None, "fresher_friendly": False}
    text_lower = text.lower()
    
    # 1. Check fresher friendly signals first
    fresher_match = re.search(
        r'(fresh graduate|fresher|0\s*(?:-|to|–)\s*1?\s*(?:years?|yrs?)|entry level|early career|recent graduates?|no experience required)', 
        text_lower
    )
    if fresher_match:
        exp["fresher_friendly"] = True
        exp["experience_min"] = 0
        
    # 2. Extract numeric ranges (e.g. 3-5 years, 3 to 5 yrs)
    range_match = re.search(r'(\d+)\s*(?:-|to|–)\s*(\d+)\+?\s*(?:years?|yrs?|Yrs)', text, re.IGNORECASE)
    if range_match:
        exp["experience_min"] = int(range_match.group(1))
        exp["experience_max"] = int(range_match.group(2))
        if exp["experience_min"] == 0:
            exp["fresher_friendly"] = True
        return exp
        
    # 3. Extract bounds like "3+ years", "at least 3 years", "minimum 3 years"
    plus_match = re.search(r'(?:minimum|at\s+least|have)?\s*(\d+)\+?\s*(?:or\s+more\s+)?(?:years?|yrs?|Yrs)', text, re.IGNORECASE)
    if plus_match:
        exp["experience_min"] = int(plus_match.group(1))
        if exp["experience_min"] == 0:
            exp["fresher_friendly"] = True
        return exp
        
    # If no match but identified as fresher friendly, set min to 0
    if exp["fresher_friendly"]:
        exp["experience_min"] = 0
        
    return exp
