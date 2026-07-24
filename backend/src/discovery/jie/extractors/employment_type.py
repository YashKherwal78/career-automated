import re

def extract_employment_type(title: str, text: str) -> str:
    """Extracts employment type: Full-time, Part-time, Contract, Internship, Temporary, Freelance."""
    text_lower = text.lower() + " " + title.lower()
    
    if re.search(r'\b(intern|internship|co-op)\b', text_lower):
        return "Internship"
    if re.search(r'\b(contract|contractor|temp|temporary|consultant)\b', text_lower):
        return "Contract"
    if re.search(r'\b(freelance|freelancer)\b', text_lower):
        return "Freelance"
    if re.search(r'\b(part-time|part\s+time)\b', text_lower):
        return "Part-time"
    if re.search(r'\b(full-time|full\s+time|permanent|fte)\b', text_lower):
        return "Full-time"
        
    return "Internship" if "intern" in title.lower() else "Full-time"
