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
            
    # 3. Match range patterns like "USD 80,000 - USD 120,000", "$80k - $120k", "10 - 15 LPA", "$50 - $70"
    # Ensure experience ranges like "1-3 years" or "5-7 yrs" are strictly ignored by checking for salary context or values >= 1000 or k/LPA suffix
    range_match = re.search(
        r'(?:salary|pay|compensation|usd|inr|gbp|eur|\$|₹|£|€)?\s*(\$|₹|£|€|USD|INR|GBP|EUR)?\s*(\d+[\d,]*)\s*(k|lpa)?\s*(?:-|to|–)\s*(\$|₹|£|€|USD|INR|GBP|EUR)?\s*(\d+[\d,]*)\s*(k|lpa)?',
        text_normalized,
        re.IGNORECASE
    )
    if range_match:
        try:
            raw_min_str = range_match.group(2).replace(",", "")
            raw_max_str = range_match.group(5).replace(",", "")
            min_val = float(raw_min_str)
            max_val = float(raw_max_str)
            full_match_text = text_normalized[range_match.start():range_match.end()].lower()

            # Ignore experience matches like "1 - 3 years"
            surrounding_context = text_normalized[max(0, range_match.start() - 10):min(len(text_normalized), range_match.end() + 15)].lower()
            if "year" in surrounding_context or "yr" in surrounding_context or "exp" in surrounding_context:
                # Unless explicit currency symbol or salary keyword is attached
                if not any(kw in surrounding_context for kw in ["salary", "pay", "comp", "$", "usd", "inr", "lpa"]):
                    return sal

            # Suffix handling
            if "k" in full_match_text:
                if min_val < 1000: min_val *= 1000
                if max_val < 1000: max_val *= 1000
            elif "lpa" in full_match_text:
                sal["currency"] = "INR"
                if min_val < 100: min_val *= 100000
                if max_val < 100: max_val *= 100000

            # Only accept if values are realistic (> 100 for yearly, or > 5 for hourly)
            if max_val >= 10 or sal["period"] == "Hourly":
                sal["minimum"] = int(min_val)
                sal["maximum"] = int(max_val)
        except Exception:
            pass

    return sal
