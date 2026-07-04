import json
from groq import Groq
from groq import Groq
from src.config.config import Config
from src.utils.groq_manager import GroqManager

class CriticRejection(Exception):
    pass

class EmailCritic:
    def __init__(self):
        self.banned_phrases = [
            "operates in a domain where",
            "critical yet overlooked",
            "emotional ownership",
            "central to your domain",
            "i would love to learn more",
            "closely aligned with",
            "deeply resonates",
            "please consider me",
            "i am passionate about",
            "passionate about",
            "i would appreciate being considered",
            "i believe i am a great fit",
            "kindly find attached",
            "i am writing to express interest",
            "resume attached for reference",
            "work in advertising services",
            "innovative approaches",
            "exciting opportunity",
            "strong fit",
            "aligns with",
            "contribute to",
            "valuable experience",
            "industry-leading",
            "cutting-edge",
            "impressed by",
            "thrilled",
            "eager",
            "opportunity to contribute"
        ]
        
        self.banned_placeholders = [
            "[recruiter name]",
            "[name]",
            "{name}",
            "{recruiter}",
            "[first name]",
            "{first name}",
            "hi ,",
            "hello ,",
            "dear ,"
        ]

    def evaluate(self, body: str, company: str, project: str, domain: str = "") -> dict:
        print("EmailCritic: Running deterministic validation...")
        
        # Word count check
        words = body.split()
        if len(words) < 90 or len(words) > 150:
            return {"status": "FAIL", "reason": f"Word count is {len(words)} (must be 90-150)."}
            
        # Banned phrases check
        body_lower = body.lower()
        
        dynamic_banned = list(self.banned_phrases)
        domain_lower = domain.lower()
        industrial_keywords = ["manufacturing", "ev", "automotive", "industrial", "operations", "supply chain", "logistics"]
        
        if any(k in domain_lower for k in industrial_keywords):
            dynamic_banned.extend([
                "audience engagement", 
                "content creation", 
                "creator economy", 
                "user retention",
                "personalized content"
            ])
            
        for phrase in dynamic_banned:
            if phrase in body_lower:
                return {"status": "FAIL", "reason": f"Contains banned phrase: '{phrase}'"}
                
        # Unresolved placeholder check
        for ph in self.banned_placeholders:
            if ph in body_lower:
                return {"status": "FAIL", "reason": f"Contains unresolved placeholder or empty name: '{ph}'"}
                
        # Basic mention checks
        if company.lower() not in body_lower and len(company) > 3:
            return {"status": "FAIL", "reason": f"Company '{company}' not mentioned."}
            
        # If it passes all deterministic checks, we just PASS. No LLM used!
        return {"status": "PASS", "reason": "Passed all deterministic checks."}
