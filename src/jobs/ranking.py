from src.system.logger import setup_logger
logger = setup_logger('ranking')
import re
import json
import yaml
import sqlite3
import os
from datetime import datetime, timezone
from src.config.config import Config
from typing import Dict, Tuple

# Load user preferences
PREFS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_preferences.yaml')
try:
    with open(PREFS_PATH, 'r') as f:
        PREFS = yaml.safe_load(f)
except FileNotFoundError:
    PREFS = {}

def parse_date(date_str: str) -> int:
    if not date_str:
        return 999
    try:
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        delta = datetime.utcnow() - dt
        return max(0, delta.days)
    except Exception:
        return 999

def classify_role(title: str) -> str:
    title = title.lower()
    if re.search(r'\b(product manager|apm|product analyst)\b', title):
        return "Product"
    elif re.search(r'\b(growth)\b', title):
        return "Growth"
    elif re.search(r'\b(founder|chief of staff|strategy)\b', title):
        return "Strategy"
    elif re.search(r'\b(business analyst|data analyst|analytics)\b', title):
        return "Analytics"
    elif re.search(r'\b(ai|machine learning|data scientist|llm)\b', title):
        return "AI/Data"
    elif re.search(r'\b(software|backend|frontend|full stack|engineer|developer)\b', title):
        return "Engineering"
    return "Other"

def infer_experience(title: str, desc: str, req: str) -> str:
    text = f"{title} {desc} {req}".lower()
    if re.search(r'\b(intern|internship|new grad|graduate|fresher)\b', title):
        return "Entry Level"
    if re.search(r'\b(senior|staff|principal|director|head|vp|manager)\b', title):
        return "Senior"
    
    # Simple regex to look for YOE in text
    match = re.search(r'(\d+)(?:\s*-\s*\d+)?\+?\s*(?:years?|yrs?)(?:\s*of\s*experience)', text)
    if match:
        yoe = int(match.group(1))
        if yoe <= 2:
            return "0-2 Years"
        elif yoe <= 4:
            return "2-4 Years"
        else:
            return "5+ Years"
    
    return "Unknown"

def get_feedback_scores(conn: sqlite3.Connection) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Pre-calculate feedback scores to avoid SQLite lock errors."""
    c = conn.cursor()
    c.execute("SELECT company_name, recommended_resume, status FROM jobs WHERE status != 'New'")
    rows = c.fetchall()
    
    company_statuses = {}
    role_statuses = {}
    
    for row in rows:
        company = (row[0] or "").lower()
        role = (row[1] or "").lower()
        status = row[2]
        
        if company not in company_statuses:
            company_statuses[company] = []
        company_statuses[company].append(status)
        
        if role not in role_statuses:
            role_statuses[role] = []
        role_statuses[role].append(status)
        
    weights = {"Applied": 40, "Interview": 80, "Offer": 120, "Saved": 20, "Ignored": -20, "Rejected": -40}
    
    company_scores = {}
    for comp, stats in company_statuses.items():
        company_scores[comp] = sum([weights.get(s, 0) for s in stats])
        
    role_scores = {}
    for role, stats in role_statuses.items():
        role_scores[role] = sum([weights.get(s, 0) for s in stats])
        
    return company_scores, role_scores

def rank_opportunity(job: Dict, company_scores: Dict[str, int], role_scores: Dict[str, int]) -> Dict:
    receipt = {}
    
    title = (job.get('job_title') or '').lower()
    company = (job.get('company_name') or '').lower()
    loc = (job.get('location') or '').lower()
    desc = (job.get('job_description') or '').lower()
    req = (job.get('skills_required') or '').lower()
    source = (job.get('source') or '').lower()
    date_posted = job.get('posting_date', '')
    
    # Classifications
    role_category = classify_role(title)
    exp_level = infer_experience(title, desc, req)
    
    # 1. Role Match (Max 100)
    target_roles = [r.replace('_', ' ') for r in PREFS.get('target_roles', [])]
    role_score = 0
    if any(tr in title for tr in target_roles):
        role_score = 100
    elif role_category in ["Product", "AI/Data", "Strategy", "Growth", "Engineering"]:
        role_score = 70
    receipt["Role Match"] = role_score
    
    # 2. Experience Match (Max 90)
    exp_score = 0
    if exp_level == "Entry Level":
        exp_score = 90
    elif exp_level == "0-2 Years":
        exp_score = 80
    elif exp_level == "2-4 Years":
        exp_score = 50
    elif exp_level == "5+ Years" or exp_level == "Senior":
        exp_score = -100
    else:
        exp_score = 40
    receipt["Experience"] = exp_score
    
    # 3. Freshness (Max 70)
    days_old = parse_date(date_posted)
    freshness = max(0, 70 - (days_old * 3))
    receipt["Freshness"] = freshness
    
    # 4. Location (Max 60) & Remote (Max 20)
    loc_score = 0
    remote_score = 0
    if "india" in loc or "bengaluru" in loc or "bangalore" in loc:
        loc_score = 60
    elif "us" in loc or "united states" in loc:
        loc_score = -500
        
    if "remote" in loc or "remote" in desc:
        remote_score = 20
        
    receipt["Location"] = loc_score
    receipt["Remote"] = remote_score
    
    # 5. Company Priority (Max 80)
    # Could query DB, but relying on static proxy for now
    priority = 40
    if company in ["stripe", "groww", "cred", "razorpay"]:
        priority = 80
    receipt["Company Priority"] = priority
    
    # 6. Provider Reliability (Max 40)
    provider_score = 40 if ("greenhouse" in source or "lever" in source or "ashby" in source) else 20
    receipt["Provider"] = provider_score
    
    # 7. User Feedback
    r_score = role_scores.get(role_category.lower(), 0)
    c_score = company_scores.get(company, 0)
    raw_feedback = int((r_score * 0.7) + (c_score * 0.2))
    feedback_score = max(-100, min(100, raw_feedback))
    receipt["User Feedback"] = feedback_score
    
    # Negative Modifiers
    penalty = 0
    exclusions = PREFS.get('exclude_keywords', [])
    for ex in exclusions:
        if ex in title:
            penalty -= 50
    if penalty < 0:
        receipt["Penalty"] = penalty
        
    final_score = sum(receipt.values())
    
    return {
        "ranking_score": final_score,
        "ranking_reason": receipt, # Storing as dict, will be json.dumps later
        "recommended_resume": role_category,
        "resume_confidence": 90
    }

def apply_ranking_engine():
    logger.info("Agent 0: Applying Adaptive Opportunity Ranking (Phase 2-8)...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs")
    jobs = cursor.fetchall()
    
    company_scores, role_scores = get_feedback_scores(conn)
    
    ranked = 0
    for job in jobs:
        result = rank_opportunity(dict(job), company_scores, role_scores)
        
        cursor.execute('''
            UPDATE jobs 
            SET ranking_score = ?, 
                ranking_reason = ?, 
                recommended_resume = ?,
                resume_confidence = ?
            WHERE id = ?
        ''', (
            result["ranking_score"],
            json.dumps(result["ranking_reason"]),
            result["recommended_resume"],
            result["resume_confidence"],
            job["id"]
        ))
        ranked += 1
            
    conn.commit()
    conn.close()
    logger.info(f"Ranking Engine complete. Ranked {ranked} opportunities.")

if __name__ == "__main__":
    apply_ranking_engine()
