import re
from typing import List

BENEFITS_REGISTRY = {
    r"\b(health\s+insurance|medical|dental|vision)\b": "Health Insurance",
    r"\b(esop|stock\s+options|equity|shares)\b": "ESOP",
    r"\b(learning\s+budget|education\s+allowance|professional\s+development)\b": "Learning Budget",
    r"\b(flexible\s+hours|flexible\s+working|flex\s+time)\b": "Flexible Hours",
    r"\b(gym|fitness|wellness)\b": "Gym Membership",
    r"\b(relocation|moving\s+assistance)\b": "Relocation Support",
    r"\b(paid\s+time\s+off|pto|vacation)\b": "Paid Time Off"
}

def extract_benefits(text: str) -> List[str]:
    """Extracts benefits from the text based on standard keywords."""
    extracted = set()
    text_lower = text.lower()
    
    for pattern, canonical in BENEFITS_REGISTRY.items():
        if re.search(pattern, text_lower):
            extracted.add(canonical)
            
    return sorted(list(extracted))
