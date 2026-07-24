import re
from typing import List

# Skill registry
SKILL_REGISTRY = {
    "system design": "System Design",
    "data structures": "Data Structures", "dsa": "Data Structures",
    "algorithms": "Algorithms",
    "machine learning": "Machine Learning", "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "natural language processing": "NLP", "nlp": "NLP",
    "computer vision": "Computer Vision",
    "data analytics": "Data Analytics",
    "a/b testing": "A/B Testing", "ab testing": "A/B Testing",
    "agile": "Agile Methodology", "scrum": "Agile Methodology",
    "communication": "Communication",
    "leadership": "Leadership",
    "teamwork": "Teamwork", "collaboration": "Teamwork",
    "problem solving": "Problem Solving",
    "product management": "Product Management",
    "project management": "Project Management",
}

def extract_skills(text: str) -> List[str]:
    """Extracts professional skills from the text, separating them from technologies."""
    extracted = set()
    text_lower = text.lower()
    
    for raw, canonical in SKILL_REGISTRY.items():
        pattern = r'\b' + re.escape(raw) + r'\b'
        if re.search(pattern, text_lower):
            extracted.add(canonical)
            
    return sorted(list(extracted))
