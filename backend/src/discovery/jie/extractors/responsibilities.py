import re
from typing import List

def extract_responsibilities(text: str) -> List[str]:
    """Extracts a list of individual responsibilities from a JD."""
    responsibilities = []
    
    # 1. Locate the responsibilities section
    section_match = re.search(
        r'(?:responsibilities|what\s+you\s*\'?ll\s+do|role\s+description|key\s+duties|about\s+the\s+role):\s*(.*?)(?=\n\n|\n[A-Z][a-z]+:|\Z)', 
        text, 
        re.IGNORECASE | re.DOTALL
    )
    
    section_text = section_match.group(1) if section_match else text
    
    # 2. Extract bullet points or numbered lists
    lines = section_text.split('\n')
    for line in lines:
        line_clean = line.strip()
        # Look for bullet points (e.g. *, -, •, or digits like 1.)
        if re.match(r'^[\s\-\*•\d\.\)]+\s*([A-Z].*)', line_clean):
            bullet_text = re.sub(r'^[\s\-\*•\d\.\)]+\s*', '', line_clean).strip()
            if len(bullet_text) > 10 and bullet_text not in responsibilities:
                responsibilities.append(bullet_text)
                
    # Fallback if no bullets matched in the specific section
    if not responsibilities and section_match:
        # Split by periods if it's a paragraph
        sentences = re.split(r'\.\s+', section_text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 15:
                responsibilities.append(s_clean)
                
    return responsibilities
