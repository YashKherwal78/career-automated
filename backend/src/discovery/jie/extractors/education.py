import re
from typing import List

DEGREES = {
    r"\b(bachelor'?s?|b\.?s\.?|b\.?e\.?|b\.?tech)\b": "Bachelor's",
    r"\b(master'?s?|m\.?s\.?|m\.?tech|m\.?b\.?a)\b": "Master's",
    r"\b(ph\.?d\.?|doctorate)\b": "PhD",
    r"\b(diploma|associate'?s?)\b": "Diploma"
}

FIELDS = {
    r"\b(computer\s+science|cs)\b": "Computer Science",
    r"\b(information\s+technology|it)\b": "Information Technology",
    r"\b(electronics|electrical|ece|ee)\b": "Electronics & Electrical Engineering",
    r"\b(mechanical\s+engineering|me)\b": "Mechanical Engineering",
    r"\b(data\s+science|ds|machine\s+learning|ml)\b": "Data Science & ML"
}

def extract_education(text: str) -> List[str]:
    """Extracts matched education degrees and fields of study."""
    extracted = []
    text_lower = text.lower()
    
    for pattern, name in DEGREES.items():
        if re.search(pattern, text_lower):
            if name not in extracted:
                extracted.append(name)
                
    for pattern, name in FIELDS.items():
        if re.search(pattern, text_lower):
            if name not in extracted:
                extracted.append(name)
                
    return extracted
