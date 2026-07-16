from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('application_judge')
import sqlite3
import json
import datetime
from src.utils.llm_router import LLMRouter
from src.config.config import Config

JUDGE_VERSION = "1.0"

JUDGE_SYSTEM_PROMPT = """
You are the Application Judge. You act as the final human-in-the-loop decision maker for Yash Kherwal.

Candidate Profile:
- Education: IIT Roorkee, Chemical Engineering
- Focus: AI and Product
- Availability: Seeking Full-Time roles

Role Preferences:
- Preferred: Product Analyst, Product Operations, Growth, APM, Data Analyst, AI Engineer
- Acceptable: SWE, Data Scientist
- Avoid/Reject: Content, Design, Marketing-heavy, Research-heavy, PhD-oriented

Employment Type Preference:
Full Time > New Grad > Internship. 
Internships should only receive a STRONG_APPLY if they are exceptionally valuable (e.g., highly relevant AI/Product roles at top startups/BigTech).

Your job is to read the job details and decide: "Would Yash realistically spend time applying to this role?"

Respond ONLY with a valid JSON object in this exact format:
{
    "decision": "STRONG_APPLY" | "APPLY" | "MAYBE" | "REJECT",
    "confidence": <integer 0-100>,
    "reasoning": "<short string explaining why based on the candidate profile>"
}
Do not include markdown blocks, just the raw JSON.
"""

class ApplicationJudge:
    def __init__(self):
        self.conn = get_connection()
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.client = LLMRouter()
        
    def evaluate_queue(self):
        logger.info("Agent 4: Initiating Application Judge V1...")
        
        # Fetch Top 50 mathematically ranked jobs
        self.cursor.execute("""
            SELECT id, job_title, company_name, location, employment_type, experience_required, 
                   job_description, ranking_score, ranking_reason, judge_version 
            FROM jobs 
            WHERE eligibility_status = 'Eligible'
            ORDER BY ranking_score DESC 
            LIMIT 50
        """)
        top_jobs = self.cursor.fetchall()
        
        judged_count = 0
        stats = {
            "STRONG_APPLY": 0,
            "APPLY": 0,
            "MAYBE": 0,
            "REJECT": 0
        }
        
        for job in top_jobs:
            if job["judge_version"] == JUDGE_VERSION:
                # Cache hit
                decision = self.cursor.execute("SELECT judge_decision FROM jobs WHERE id = ?", (job["id"],)).fetchone()[0]
                if decision in stats:
                    stats[decision] += 1
                continue
                
            logger.info(f"Judging: {job['job_title']} at {job['company_name']}...")
            
            # Truncate description to save tokens
            desc = (job["job_description"] or "")[:3000]
            
            user_prompt = f"""
            TITLE: {job['job_title']}
            COMPANY: {job['company_name']}
            LOCATION: {job['location']}
            EMPLOYMENT TYPE: {job['employment_type']}
            EXPERIENCE: {job['experience_required']}
            RANKING SCORE: {job['ranking_score']}
            RANKING REASONS: {job['ranking_reason']}
            
            DESCRIPTION EXCERPT:
            {desc}
            """
            
            try:
                response = self.client.chat_completion(
                    messages=[
                        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    intent="reasoning"
                )
                
                content = response.choices[0].message.content.strip()
                # Clean up potential markdown formatting
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                    
                result = json.loads(content)
                decision = result.get("decision", "MAYBE")
                confidence = result.get("confidence", 50)
                reasoning = result.get("reasoning", "Parsed fallback")
                
                # Verify schema
                if decision not in ["STRONG_APPLY", "APPLY", "MAYBE", "REJECT"]:
                    decision = "MAYBE"
                    
            except Exception as e:
                logger.info(f"LLM Error on job {job['id']}: {e}")
                decision = "MAYBE"
                confidence = 0
                reasoning = "LLM Failure"
                
            # Persist judgment
            now = datetime.datetime.now().isoformat()
            self.cursor.execute('''
                UPDATE jobs 
                SET judge_decision = ?, 
                    judge_reasoning = ?, 
                    judge_confidence = ?, 
                    judge_version = ?, 
                    judge_timestamp = ?
                WHERE id = ?
            ''', (decision, reasoning, confidence, JUDGE_VERSION, now, job["id"]))
            self.conn.commit()
            
            stats[decision] += 1
            judged_count += 1
            
        # Analytics
        logger.info("\n========================================")
        logger.info(" APPLICATION JUDGE V1 ANALYTICS ")
        logger.info("========================================")
        logger.info(f"Total Top 50 Processed: 50")
        logger.info(f"Newly Judged This Run:  {judged_count}")
        logger.info(f"STRONG_APPLY Count:     {stats['STRONG_APPLY']}")
        logger.info(f"APPLY Count:            {stats['APPLY']}")
        logger.info(f"MAYBE Count:            {stats['MAYBE']}")
        logger.info(f"REJECT Count:           {stats['REJECT']}")
        
        override_rate = (stats['MAYBE'] + stats['REJECT']) / 50.0 * 100
        logger.info(f"Judge Override Rate:    {override_rate:.1f}%")
        logger.info("========================================\n")

if __name__ == "__main__":
    judge = ApplicationJudge()
    judge.evaluate_queue()
