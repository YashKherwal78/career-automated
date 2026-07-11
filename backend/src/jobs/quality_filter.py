from src.system.logger import setup_logger
logger = setup_logger('quality_filter')
import re
import sqlite3
from src.config.config import Config
from typing import Tuple

def evaluate_job_quality(job_title: str) -> Tuple[int, str]:
    """
    Evaluates job title for seniority penalties and role boosts.
    Returns (quality_score, quality_reason).
    """
    score = 0
    reasons = []
    
    title_lower = job_title.lower()
    
    # Penalties
    if re.search(r'\bvp\b|\bvice president\b', title_lower):
        score -= 500
        reasons.append("VP Penalty (-500)")
    elif re.search(r'\bdirector\b', title_lower):
        score -= 300
        reasons.append("Director Penalty (-300)")
    elif re.search(r'\bprincipal\b', title_lower):
        score -= 200
        reasons.append("Principal Penalty (-200)")
    elif re.search(r'\bstaff\b', title_lower):
        score -= 150
        reasons.append("Staff Penalty (-150)")
    elif re.search(r'\bsenior\b|\bsr\.?\b', title_lower):
        score -= 100
        reasons.append("Senior Penalty (-100)")
    elif re.search(r'\bphd\b', title_lower):
        score -= 100
        reasons.append("PhD Penalty (-100)")
        
    # Boosts
    boosts = {
        r'\bai engineer\b': 20,
        r'\bml engineer\b': 20,
        r'\bmachine learning engineer\b': 20,
        r'\bapplied ai\b': 20,
        r'\bai product manager\b': 20,
        r'\bproduct analyst\b': 20,
        r'\bdata analyst\b': 20,
        r'\bdata scientist\b': 20,
        r'\btechnical pm\b': 20,
        r'\btechnical product manager\b': 20
    }
    
    for pattern, boost_val in boosts.items():
        if re.search(pattern, title_lower):
            score += boost_val
            reasons.append(f"Role Boost (+{boost_val})")
            break # Apply one boost max
            
    reason_str = ", ".join(reasons) if reasons else "Neutral"
    return score, reason_str

def apply_quality_filters():
    """
    Runs over all jobs in the database and updates their quality score.
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, job_title FROM jobs")
    jobs = cursor.fetchall()
    
    for job in jobs:
        score, reason = evaluate_job_quality(job["job_title"])
        cursor.execute('''
            UPDATE jobs 
            SET quality_score = ?, quality_reason = ? 
            WHERE id = ?
        ''', (score, reason, job["id"]))
        
    conn.commit()
    conn.close()
    
if __name__ == "__main__":
    apply_quality_filters()
    logger.info("Quality filters applied successfully.")
