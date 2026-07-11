from src.system.logger import setup_logger
logger = setup_logger('project_selector')
import json
import sqlite3
from src.utils.llm_router import LLMRouter
from src.config.config import Config

class ProjectSelector:
    @staticmethod
    def _get_cached_selection(company: str):
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_selector_cache (
                    company TEXT PRIMARY KEY,
                    selected_project TEXT,
                    rejected_project TEXT,
                    reason TEXT,
                    confidence TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 30 day cache validity
            cursor.execute('''
                SELECT selected_project, rejected_project, reason, confidence 
                FROM project_selector_cache 
                WHERE company = ? AND last_updated >= datetime('now', '-30 days')
            ''', (company,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return (row[0], [row[1]], row[2], row[3])
            return None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    @staticmethod
    def _set_cached_selection(company: str, selected: str, rejected: str, reason: str, conf: str):
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO project_selector_cache (company, selected_project, rejected_project, reason, confidence, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (company, selected, rejected, reason, conf))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    @staticmethod
    def select(company: str, intel_dict: dict) -> tuple[str, list[str], str, str]:
        """
        Returns (Project, [Rejected_Project], Reasoning, Confidence)
        """
        cached = ProjectSelector._get_cached_selection(company)
        if cached:
            logger.info(f"ProjectSelector: Using cached selection for {company}")
            return cached

        domain = intel_dict.get("domain", "Other")
        domain_lower = domain.lower()
        
        # 1. Rule-based shortlist (Exactly 2 candidates)
        if any(k in domain_lower for k in ["ai", "genai", "automation", "industrial", "enterprise", "operations"]):
            shortlist = ["CareerAutomated", "GDSC Search Engine"]
        elif any(k in domain_lower for k in ["media", "consumer", "advertising", "edtech", "social"]):
            shortlist = ["YAAR", "Orange Labs"]
        elif any(k in domain_lower for k in ["fintech", "e-commerce", "analytics", "consulting", "saas"]):
            shortlist = ["Orange Labs", "CareerAutomated"]
        elif any(k in domain_lower for k in ["search", "infrastructure", "data", "cloud"]):
            shortlist = ["GDSC Search Engine", "CareerAutomated"]
        else:
            shortlist = ["CareerAutomated", "YAAR"] # Default fallback candidates
            
        proj_descriptions = {
            "CareerAutomated": "An AI-driven pipeline that automates job discovery, intelligence gathering, and applying to jobs. Built with Python, LLMs, Playwright.",
            "YAAR": "A personalized AI podcast/media generator that curates content based on user preferences.",
            "GDSC Search Engine": "A retrieval augmented generation (RAG) system for searching documentation.",
            "Orange Labs": "Growth product management and data analytics."
        }
        
        prompt = f"""
        You are an AI recruiting assistant selecting the best project from Yash Kherwal's portfolio to pitch to a company in the '{domain}' domain.
        Company Name: {company}
        Company Intelligence: {json.dumps(intel_dict)}
        
        You MUST pick exactly ONE of the following TWO projects:
        1. {shortlist[0]}: {proj_descriptions[shortlist[0]]}
        2. {shortlist[1]}: {proj_descriptions[shortlist[1]]}
        
        Return ONLY valid JSON matching this schema:
        {{
            "selected_project": "Exact name from the shortlist",
            "reason": "1 sentence explaining why this is the most relevant project",
            "confidence": "High, Medium, or Low"
        }}
        """
        
        try:
            router = LLMRouter()
            response = router.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                intent="reasoning"
            )
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            project = data.get("selected_project")
            
            if project not in shortlist:
                project = shortlist[0] # Deterministic fallback if LLM hallucinates
                
            reason = data.get("reason", "Rule-based fallback")
            conf = data.get("confidence", "Medium")
            
            rejected = shortlist[1] if project == shortlist[0] else shortlist[0]
            
            ProjectSelector._set_cached_selection(company, project, rejected, reason, conf)
            
            return (project, [rejected], reason, conf)
            
        except Exception as e:
            logger.info(f"ProjectSelector Error: {e}")
            return ("REVIEW_REQUIRED", [shortlist[0], shortlist[1]], "LLM selection failed", "Low")
