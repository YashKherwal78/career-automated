import re
import json
from typing import Dict, Any, List, Tuple

class JobQualificationExtractor:
    def __init__(self):
        self.tech_skills = ["python", "java", "sql", "fastapi", "react", "kubernetes", "docker", "llm", "langchain", "aws", "gcp", "azure", "c++", "go", "ruby", "django"]
        self.pm_skills = ["agile", "scrum", "roadmap", "a/b testing", "data analysis", "user research", "jira", "sql", "product strategy"]
        self.domains = {
            "FinTech": ["payment", "fintech", "banking", "trading", "crypto", "blockchain"],
            "Healthcare": ["health", "medical", "patient", "clinical"],
            "AI": ["artificial intelligence", "machine learning", "deep learning", "llm", "generative ai"],
            "EdTech": ["education", "learning", "student"],
            "SaaS": ["saas", "b2b", "enterprise software"]
        }
        self.signals = {
            "Immediate Joiner Preferred": ["immediate joiner", "join immediately", "urgent"],
            "Startup Experience Preferred": ["startup experience", "fast-paced environment", "scrappy"],
            "Customer-facing Role": ["client facing", "customer facing", "customer success"],
            "Technical PM": ["technical product manager", "computer science degree", "engineering background"]
        }
        
    def _extract_experience(self, text: str) -> Dict[str, Any]:
        exp = {"min": None, "max": None, "confidence": 0.0}
        
        # Match "X-Y years", "X to Y years"
        range_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\+?\s*years?', text)
        if range_match:
            exp["min"] = int(range_match.group(1))
            exp["max"] = int(range_match.group(2))
            exp["confidence"] = 0.95
            return exp
            
        # Match "X+ years", "X or more years"
        plus_match = re.search(r'(\d+)\+?\s*(?:or more\s*)?years?', text)
        if plus_match:
            exp["min"] = int(plus_match.group(1))
            exp["confidence"] = 0.90
            return exp
            
        if "fresh graduate" in text or "fresher" in text or "0 years" in text:
            exp["min"] = 0
            exp["confidence"] = 0.85
            
        return exp

    def _extract_work_mode(self, text: str) -> str:
        if "remote" in text or "work from home" in text:
            return "Remote"
        if "hybrid" in text:
            return "Hybrid"
        if "onsite" in text or "on-site" in text or "in office" in text:
            return "Onsite"
        return "Unknown"
        
    def _extract_employment(self, text: str, title: str) -> str:
        combined = text + " " + title
        if "intern" in combined:
            return "Internship"
        if "contract" in combined:
            return "Contract"
        if "part-time" in combined or "part time" in combined:
            return "Part-time"
        return "Full-time"
        
    def _extract_skills(self, text: str) -> Tuple[List[str], List[str]]:
        required = set()
        preferred = set()
        
        # Extremely basic heuristic: if "preferred" or "nice to have" appears, subsequent matched skills are preferred
        # For this prototype, we'll just scan all and put them in required
        for skill in self.tech_skills + self.pm_skills:
            # use word boundaries to avoid matching subwords
            if re.search(r'\b' + re.escape(skill) + r'\b', text):
                if skill == "llm":
                    required.add("LLMs")
                else:
                    required.add(skill.capitalize() if len(skill) > 3 else skill.upper())
                    
        return list(required), list(preferred)
        
    def _extract_domain(self, text: str) -> str:
        for domain, keywords in self.domains.items():
            for kw in keywords:
                if kw in text:
                    return domain
        return "Unknown"
        
    def _extract_signals(self, text: str) -> List[str]:
        found_signals = []
        for signal, keywords in self.signals.items():
            for kw in keywords:
                if kw in text:
                    found_signals.append(signal)
                    break
        return found_signals

    def extract(self, title: str, jd_text: str) -> Dict[str, Any]:
        text_lower = jd_text.lower()
        title_lower = title.lower()
        
        req_skills, pref_skills = self._extract_skills(text_lower)
        
        return {
            "experience": self._extract_experience(text_lower),
            "employment": self._extract_employment(text_lower, title_lower),
            "work_mode": self._extract_work_mode(text_lower),
            "required_skills": req_skills,
            "preferred_skills": pref_skills,
            "domain": self._extract_domain(text_lower),
            "signals": self._extract_signals(text_lower),
            "confidence": 0.85 # Average confidence of deterministic parsing
        }
