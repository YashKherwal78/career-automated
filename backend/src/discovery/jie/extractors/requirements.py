import re
from typing import List, Dict, Any
from src.discovery.jie.models import Requirement

def extract_requirements(text: str) -> List[str]:
    """Extracts requirements / qualifications from the text."""
    requirements = []
    
    # Locate requirements section
    section_match = re.search(
        r'(?:requirements|qualifications|what\s+you\s+bring|basic\s+skills|preferred\s+skills):\s*(.*?)(?=\n\n|\n[A-Z][a-z]+:|\Z)', 
        text, 
        re.IGNORECASE | re.DOTALL
    )
    
    section_text = section_match.group(1) if section_match else text
    
    lines = section_text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if re.match(r'^[\s\-\*•\d\.\)]+\s*([A-Z].*)', line_clean):
            bullet_text = re.sub(r'^[\s\-\*•\d\.\)]+\s*', '', line_clean).strip()
            if len(bullet_text) > 10 and bullet_text not in requirements:
                requirements.append(bullet_text)
                
    # Fallback to sentences if no bullet lists matched
    if not requirements and section_match:
        sentences = re.split(r'\.\s+', section_text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 15:
                requirements.append(s_clean)
                
    return requirements

def generate_legacy_requirements(requirements_list: List[str], tech_list: List[str], skills_list: List[str]) -> List[Requirement]:
    """Generates legacy Requirement objects for backward compatibility."""
    legacy = []
    
    # Convert extracted technologies to Requirement models
    for tech in tech_list:
        legacy.append(Requirement(
            type="skill",
            name=tech,
            importance="REQUIRED",
            confidence=0.95,
            evidence="Extracted from technologies list."
        ))
        
    for skill in skills_list:
        legacy.append(Requirement(
            type="skill",
            name=skill,
            importance="REQUIRED",
            confidence=0.95,
            evidence="Extracted from skills list."
        ))
        
    return legacy
