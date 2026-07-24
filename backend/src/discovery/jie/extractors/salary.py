import re
from typing import Dict, Any

def extract_salary(text: str) -> Dict[str, Any]:
    """Extracts salary currency, minimum, maximum, and period."""
    sal = {"currency": "", "minimum": None, "maximum": None, "period": ""}
    
    # Clean text to normalize currency symbols and abbreviations
    text_normalized = text.replace("$", "USD ").replace("₹", "INR ").replace("£", "GBP ").replace("€", "EUR ")
    
    # 1. Period detection
    if re.search(r'\b(hourly|hour|hr|/hr|/hour)\b', text_normalized, re.IGNORECASE):
        sal["period"] = "Hourly"
    elif re.search(r'\b(monthly|month|mo|/mo|/month)\b', text_normalized, re.IGNORECASE):
        sal["period"] = "Monthly"
    else:
        sal["period"] = "Yearly"
        
    # 2. Currency detection
    for symbol, name in [("USD", "USD"), ("INR", "INR"), ("GBP", "GBP"), ("EUR", "EUR"), ("LPA", "INR"), ("CAD", "CAD")]:
        if symbol in text_normalized:
            sal["currency"] = name
            break
            
    # 3. Match range patterns like "USD 80,000 - USD 120,000", "USD 50 - 70 / hr", "10 - 15 LPA"
    # Matches simple ranges with or without k/LPA suffix
    range_match = re.search(
        r'(?:USD|INR|GBP|EUR)?\s*(\d+[\d,]*)\s*(?:k|LPA)?\s*(?:-|to|–)\s*(?:USD|INR|GBP|EUR)?\s*(\d+[\d,]*)\s*(k|LPA)?',
        text_normalized,
        re.IGNORECASE
    )
    if range_match:
        try:
            min_val = float(range_match.group(1).replace(",", ""))
            max_val = float(range_match.group(2).replace(",", ""))
            suffix = range_match.group(3) or ""
            
            # Normalize suffixes (k -> * 1000, LPA -> * 100000)
            if "k" in text_normalized[range_match.start():range_match.end()].lower() or suffix.lower() == "k":
                if min_val < 1000: min_val *= 1000
                if max_val < 1000: max_val *= 1000
            elif "lpa" in text_normalized[range_match.start():range_match.end()].lower() or suffix.lower() == "lpa":
                sal["currency"] = "INR"
                if min_val < 100: min_val *= 100000
                if max_val < 100: max_val *= 100000
                
            sal["minimum"] = int(min_val)
            sal["maximum"] = int(max_val)
        except Exception:
            pass
            
    return sal
