import hashlib
import datetime
import re
from typing import Dict, Any, List

from src.discovery.jie.models import StructuredJob, Requirement

JIE_VERSION = "1.0.0"

class JDExtractor:
    def __init__(self):
        pass

    def _hash_jd(self, jd_text: str) -> str:
        return hashlib.md5(jd_text.encode('utf-8')).hexdigest()

    def _extract_experience(self, text: str) -> Dict[str, Any]:
        exp = {"min": None, "max": None, "confidence": 0.0, "evidence": ""}
        
        # Match "X-Y years", "X to Y yrs", "X - Y Yrs"
        range_match = re.search(r'(\d+)\s*(?:-|to|–)\s*(\d+)\+?\s*(?:years?|yrs?|Yrs)', text, re.IGNORECASE)
        if range_match:
            exp["min"] = int(range_match.group(1))
            exp["max"] = int(range_match.group(2))
            exp["confidence"] = 0.95
            start = max(0, range_match.start() - 30)
            end = min(len(text), range_match.end() + 30)
            exp["evidence"] = text[start:end].strip()
            return exp
            
        # Match "X+ years", "X or more yrs", "Minimum X years"
        plus_match = re.search(r'(?:minimum\s*)?(\d+)\+?\s*(?:or more\s*)?(?:years?|yrs?|Yrs)', text, re.IGNORECASE)
        if plus_match:
            exp["min"] = int(plus_match.group(1))
            exp["confidence"] = 0.90
            start = max(0, plus_match.start() - 30)
            end = min(len(text), plus_match.end() + 30)
            exp["evidence"] = text[start:end].strip()
            return exp
            
        # Match qualitative phrases
        fresh_match = re.search(r'(fresh graduate|fresher|0 years|entry level|early career|recent graduates? welcome)', text, re.IGNORECASE)
        if fresh_match:
            exp["min"] = 0
            exp["confidence"] = 0.85
            start = max(0, fresh_match.start() - 30)
            end = min(len(text), fresh_match.end() + 30)
            exp["evidence"] = text[start:end].strip()
            return exp
            
        experienced_match = re.search(r'(experienced professional|proven experience)', text, re.IGNORECASE)
        if experienced_match:
            exp["min"] = 3
            exp["confidence"] = 0.40 # low confidence
            start = max(0, experienced_match.start() - 30)
            end = min(len(text), experienced_match.end() + 30)
            exp["evidence"] = text[start:end].strip()
            return exp
            
        return exp

    def _extract_work_mode(self, text: str) -> str:
        if re.search(r'(remote|work from home)', text, re.IGNORECASE):
            return "Remote"
        if "hybrid" in text.lower():
            return "Hybrid"
        if re.search(r'(onsite|on-site|in office)', text, re.IGNORECASE):
            return "Onsite"
        return "Unknown"

    def _extract_skills(self, text: str) -> List[Requirement]:
        requirements = []
        # Basic heuristic for sprint 1.6
        skills_to_check = ["python", "java", "sql", "fastapi", "react", "kubernetes", "docker", "llm", "langchain", "aws", "product management", "a/b testing"]
        
        text_lower = text.lower()
        for skill in skills_to_check:
            match = re.search(r'\b' + re.escape(skill) + r'\b', text_lower)
            if match:
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                evidence = text[start:end].strip()
                
                importance = "REQUIRED"
                if "prefer" in evidence.lower() or "nice to have" in evidence.lower() or "bonus" in evidence.lower():
                    importance = "PREFERRED"
                    
                req = Requirement(
                    type="skill",
                    name=skill,
                    importance=importance,
                    confidence=0.90,
                    evidence=evidence
                )
                requirements.append(req)
        return requirements

    def extract(self, title: str, jd_text: str) -> StructuredJob:
        jd_hash = self._hash_jd(jd_text)
        parsed_at = datetime.datetime.utcnow().isoformat() + "Z"
        
        # 1. Experience
        exp_data = self._extract_experience(jd_text)
        requirements = self._extract_skills(jd_text)
        
        if exp_data["min"] is not None:
            requirements.append(Requirement(
                type="experience",
                name="Years of Experience",
                importance="REQUIRED",
                confidence=exp_data["confidence"],
                evidence=exp_data["evidence"]
            ))
            
        # Mocking responsibilities for V1.6
        responsibilities = []
        if "responsibilit" in jd_text.lower():
            responsibilities.append("Derived responsibility from JD.")
            
        return StructuredJob(
            jd_hash=jd_hash,
            jie_version=JIE_VERSION,
            parsed_at=parsed_at,
            experience_min=exp_data["min"],
            experience_max=exp_data["max"],
            employment_type="Full-time" if "intern" not in title.lower() else "Internship",
            work_mode=self._extract_work_mode(jd_text),
            domain="Unknown",
            requirements=requirements,
            responsibilities=responsibilities,
            benefits=[],
            hiring_signals=[]
        )
