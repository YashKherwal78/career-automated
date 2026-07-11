from src.system.logger import setup_logger
logger = setup_logger('scoring_engine')
import yaml
import sqlite3
import json
import re

class JobScoringEngine:
    def __init__(self, db_path="data/crm.db", config_path="config/scoring_profiles.yaml", profile_name="ai_engineer"):
        self.db_path = db_path
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)["profiles"][profile_name]
            
    def _score_text(self, text: str, weights: dict, breakdown: list):
        if not text: return 0, False
        score = 0
        found_any = False
        text_lower = text.lower()
        for kw, w in weights.get("positive", {}).items():
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text_lower):
                score += w
                breakdown.append(f"+{kw}")
                found_any = True
        for kw, w in weights.get("negative", {}).items():
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text_lower):
                score += w
                breakdown.append(f"{kw}")
                found_any = True
        return score, found_any

    def score_job(self, job: dict) -> tuple:
        breakdown = []
        full_text = f"{job.get('title', '')} {job.get('description', '')}"
        
        # Match Score
        tech_score, t_found = self._score_text(full_text, self.config["match"]["technology"], breakdown)
        role_score, r_found = self._score_text(job.get("title", ""), self.config["match"]["role"], breakdown)
        
        # Experience (Simplified)
        exp_score = 0
        if "5+ years" in full_text.lower() or "senior" in job.get("title", "").lower():
            exp_score = -15
            breakdown.append("-5+ years req")
        
        match_score = tech_score + role_score + exp_score
        
        # Priority Score
        loc_score, _ = self._score_text(job.get("location", ""), {"positive": self.config["priority"]["logistics"]}, breakdown)
        comp_score, _ = self._score_text(full_text, {"positive": self.config["priority"]["company"]}, breakdown)
        
        priority_score = loc_score + comp_score
        
        total = match_score + priority_score
        
        # Confidence
        confidence = 1.0
        if not job.get("description"): confidence -= 0.5
        if not t_found and not r_found: confidence -= 0.2
        confidence = max(0.1, confidence)
        
        # Recommendation Reason
        reason = f"Scored {total} ({match_score} Match, {priority_score} Priority)."
        if tech_score > 0 and comp_score > 0:
            reason = "Excellent fit because it is a high-priority startup matching your core tech stack."
        elif match_score > 20:
            reason = "Strong role match, but standard priority."
        elif total < 0:
            reason = "Poor fit based on role seniority or missing tech stack."
            
        return total, match_score, priority_score, confidence, reason, breakdown

    def run(self):
        logger.info("========== RUNNING SCORING ENGINE ==========")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT job_id, title, location, description FROM normalized_jobs WHERE status = 'ACTIVE'")
        jobs = c.fetchall()
        
        updates = []
        for jid, title, loc, desc in jobs:
            job_dict = {"title": title, "location": loc, "description": desc}
            total, m_score, p_score, conf, reason, breakdown = self.score_job(job_dict)
            updates.append((total, m_score, p_score, conf, reason, json.dumps(breakdown), jid))
            
        c.executemany('''
            UPDATE normalized_jobs 
            SET job_score = ?, match_score = ?, priority_score = ?, scoring_confidence = ?, recommendation_reason = ?, score_breakdown = ? 
            WHERE job_id = ?
        ''', updates)
        conn.commit()
        logger.info(f"Scored {len(jobs)} active jobs successfully.")
        conn.close()

if __name__ == "__main__":
    JobScoringEngine().run()
