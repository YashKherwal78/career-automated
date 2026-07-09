from src.system.logger import setup_logger
logger = setup_logger('critic')
import json
from src.utils.llm_router import LLMRouter

class CriticRejection(Exception):
    pass

class EmailCritic:
    def __init__(self):
        self.banned_phrases = [
            "operates in a domain where", "critical yet overlooked", "emotional ownership",
            "central to your domain", "i would love to learn more", "closely aligned with",
            "deeply resonates", "please consider me", "i am passionate about", "passionate about",
            "i would appreciate being considered", "i believe i am a great fit", "kindly find attached",
            "i am writing to express interest", "resume attached for reference", "work in advertising services",
            "innovative approaches", "exciting opportunity", "strong fit", "aligns with", "contribute to",
            "valuable experience", "industry-leading", "cutting-edge", "impressed by", "thrilled",
            "eager", "opportunity to contribute"
        ]
        
        self.banned_placeholders = [
            "[recruiter name]", "[name]", "{name}", "{recruiter}", "[first name]", "{first name}",
            "hi ,", "hello ,", "dear ,"
        ]

    def evaluate(self, body: str, company: str, project: str, domain: str = "") -> dict:
        logger.info("EmailCritic: Running evaluation scorecard...")
        
        scorecard = {
            "Greeting": "FAIL",
            "Company Mention": "FAIL",
            "Project Mention": "FAIL",
            "Company Research Used": "FAIL",
            "Networking Tone": "FAIL",
            "Placeholder Check": "FAIL",
            "Generic AI Phrase Check": "FAIL",
            "Word Count": "FAIL",
            "Grammar": "PASS", # Default pass unless flagged
            "Overall Score": "0/100",
            "status": "FAIL",
            "reason": ""
        }
        score = 0
        max_score = 100
        
        body_lower = body.lower()
        
        # 1. Greeting
        if any(g in body_lower for g in ["hi ", "hello "]) and not any(ph in body_lower for ph in ["hi ,", "hello ,"]):
            scorecard["Greeting"] = "PASS"
            score += 10
            
        # 2. Company Mention
        if company.lower() in body_lower and len(company) > 3:
            scorecard["Company Mention"] = "PASS"
            score += 15
            
        # 3. Project Mention
        if project.lower() in body_lower or any(p in body_lower for p in ["careerautomated", "yaar", "gdsc", "orange labs"]):
            scorecard["Project Mention"] = "PASS"
            score += 15
            
        # 4. Placeholder Check
        if not any(ph in body_lower for ph in self.banned_placeholders):
            scorecard["Placeholder Check"] = "PASS"
            score += 10
            
        # 5. Generic AI Phrase Check
        dynamic_banned = list(self.banned_phrases)
        industrial_keywords = ["manufacturing", "ev", "automotive", "industrial", "operations", "supply chain", "logistics"]
        if any(k in domain.lower() for k in industrial_keywords):
            dynamic_banned.extend(["audience engagement", "content creation", "creator economy", "user retention", "personalized content"])
            
        if not any(phrase in body_lower for phrase in dynamic_banned):
            scorecard["Generic AI Phrase Check"] = "PASS"
            score += 15
            
        # 6. Word Count
        words = body.split()
        if 90 <= len(words) <= 150:
            scorecard["Word Count"] = "PASS"
            score += 10
            
        # 7. LLM Evaluation for Research, Tone, Grammar
        prompt = f"""
        Evaluate the following student networking email for three criteria:
        1. Company Research Used: Does the email mention a specific challenge or domain focus of the company '{company}'?
        2. Networking Tone: Does it sound like a genuine builder/student (PASS), or does it sound overly formal/salesy/like a cover letter (FAIL)?
        3. Grammar: Are there any obvious grammatical errors? (PASS if none).
        
        Email Body:
        {body}
        
        Return ONLY valid JSON:
        {{
            "Company Research Used": "PASS or FAIL",
            "Networking Tone": "PASS or FAIL",
            "Grammar": "PASS or FAIL"
        }}
        """
        try:
            router = LLMRouter()
            response = router.chat_completion([{"role": "user", "content": prompt}], temperature=0.1, intent="utility")
            content = response.choices[0].message.content
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content: content = content.split("```")[1].strip()
            
            data = json.loads(content)
            if data.get("Company Research Used") == "PASS": 
                scorecard["Company Research Used"] = "PASS"
                score += 15
            if data.get("Networking Tone") == "PASS":
                scorecard["Networking Tone"] = "PASS"
                score += 10
            if data.get("Grammar") == "FAIL":
                scorecard["Grammar"] = "FAIL"
        except Exception as e:
            logger.info(f"Critic LLM Error: {e}. Falling back to default FAIL for soft skills.")
            
        scorecard["Overall Score"] = f"{score}/{max_score}"
        
        if score >= 90 and scorecard["Placeholder Check"] == "PASS" and scorecard["Generic AI Phrase Check"] == "PASS":
            scorecard["status"] = "PASS"
            scorecard["reason"] = "Passed high-bar evaluation."
        else:
            scorecard["status"] = "FAIL"
            scorecard["reason"] = f"Failed to meet quality bar. Score: {score}"
            
        return scorecard
