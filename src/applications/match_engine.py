from src.system.logger import setup_logger
logger = setup_logger('match_engine')
import json
import os
from src.config.config import Config

class MatchEngine:
    """
    Evaluates discovered jobs against the Candidate Intelligence DB
    Returns a score from 0-100 and a rejection reason if it fails.
    """
    def __init__(self):
        self.profile_path = os.path.join(Config.DATA_DIR, "context", "master_candidate_profile.json")
        self.profile = self._load_profile()
        self.threshold = 75
        
        # High value roles get a bonus
        self.bonus_roles = [
            "ai product manager",
            "associate product manager",
            "product manager",
            "ai engineer",
            "applied ai engineer",
            "llm engineer",
            "founder's office",
            "genai engineer"
        ]
        
    def _load_profile(self):
        if not os.path.exists(self.profile_path):
            return {}
        try:
            with open(self.profile_path, 'r') as f:
                return json.load(f)
        except:
            return {}
            
    def evaluate(self, job_title: str, company: str, location: str, job_description: str, employee_count: str = "") -> dict:
        title_lower = job_title.lower()
        jd_lower = job_description.lower() if job_description else ""
        emp_lower = employee_count.lower() if employee_count else ""
        
        # --- HARD REJECT STAGE ---
        senior_keywords = ["senior", "staff", "principal", "lead", "director"]
        if any(kw in title_lower for kw in senior_keywords):
            return {
                "opportunity_score": 0, "role_fit": 0, "company_fit": 0, "interview_probability": 0,
                "passed": False, "rejection_reason": "Senior Role", "why_this_job": ""
            }
            
        if "5+ years" in jd_lower or "10+ years" in jd_lower or "8+ years" in jd_lower:
            return {
                "opportunity_score": 0, "role_fit": 0, "company_fit": 0, "interview_probability": 0,
                "passed": False, "rejection_reason": "Experience Mismatch", "why_this_job": ""
            }
            
        why_bullets = []
        
        # 1. Role Fit Score (0-40)
        role_fit = 20
        role_matched = False
        if any(role in title_lower for role in self.bonus_roles):
            role_fit += 20 # Bonus weighting
            role_matched = True
            why_bullets.append("* High-priority target role")
        elif "engineer" in title_lower or "analyst" in title_lower:
            role_fit += 10
            why_bullets.append("* Technical role match")
            
        # 2. Company Fit / Domain Score (0-30)
        company_fit = 15
        if "ai" in jd_lower or "machine learning" in jd_lower or "genai" in jd_lower:
            company_fit += 15
            why_bullets.append("* AI/GenAI Domain match")
        else:
            company_fit -= getattr(Config, "PENALTY_DOMAIN", 15)
            
        # Startup Bonus
        if "1-10" in emp_lower or "11-50" in emp_lower or ("employees" in emp_lower and int(''.join(filter(str.isdigit, emp_lower.split('-')[0] if '-' in emp_lower else emp_lower)) or 0) <= 50):
            company_fit += 15
            why_bullets.append("* Early-stage startup (0-50 employees)")
        elif "51-200" in emp_lower or ("employees" in emp_lower and int(''.join(filter(str.isdigit, emp_lower.split('-')[0] if '-' in emp_lower else emp_lower)) or 0) <= 200):
            company_fit += 10
            why_bullets.append("* Mid-stage startup (50-200 employees)")
        elif "201-500" in emp_lower or ("employees" in emp_lower and int(''.join(filter(str.isdigit, emp_lower.split('-')[0] if '-' in emp_lower else emp_lower)) or 0) <= 500):
            company_fit += 5
            why_bullets.append("* Late-stage startup (200-500 employees)")
        elif "1000+" in emp_lower or "enterprise" in jd_lower:
            company_fit -= getattr(Config, "PENALTY_ENTERPRISE", 15)
            
        company_fit = max(0, min(30, company_fit))
            
        # 3. Interview Probability / Location & Experience (0-30)
        interview_prob = 15
        if "remote" in location.lower():
            interview_prob += 15
            why_bullets.append("* Remote location")
        elif any(loc in location.lower() for loc in ["bangalore", "bengaluru", "gurgaon", "noida", "hyderabad", "mumbai"]):
            interview_prob += 10
            why_bullets.append(f"* Preferred location ({location})")
            
        # Penalties
        if "3+ years" in jd_lower or "4+ years" in jd_lower:
            interview_prob -= getattr(Config, "PENALTY_EXPERIENCE", 30)
            
        if "phd" in jd_lower or "master's degree" in jd_lower:
            interview_prob -= getattr(Config, "PENALTY_DEGREE", 20)
             
        # Aggregate
        total_score = max(0, min(100, role_fit + company_fit + interview_prob))
        
        why_this_job = "\n".join(why_bullets) if why_bullets else "* Standard matching parameters"
        
        reason = None
        if total_score < self.threshold:
            if company_fit <= 0:
                reason = "Wrong Domain or Enterprise Role"
            elif interview_prob <= 0:
                reason = "Experience or Degree Penalty"
            else:
                reason = "Low Opportunity Score"
                
        return {
            "overall_score": total_score,
            "raw_score": total_score,
            "role_fit": role_fit,
            "company_fit": company_fit,
            "interview_probability": interview_prob,
            "passed": total_score >= self.threshold,
            "reasoning": reason if reason else why_this_job
        }
        
    def normalize_batch(self, scored_jobs: list) -> list:
        """
        Enforces the V1.4 target distribution by percentiles:
        Top 5% -> 90+
        Top 15% -> 80-90
        Top 30% -> 70-80
        Remaining -> Below 70
        """
        # Filter out hard rejects (score 0) before normalizing
        valid_jobs = [j for j in scored_jobs if j.get('raw_score', 0) > 0]
        rejects = [j for j in scored_jobs if j.get('raw_score', 0) == 0]
        
        valid_jobs.sort(key=lambda x: x.get('raw_score', 0), reverse=True)
        total = len(valid_jobs)
        
        for rank, job in enumerate(valid_jobs):
            percentile = rank / total if total > 0 else 0
            
            # Map raw score to normalized score band
            if percentile <= 0.05:
                # Top 5% -> 90 to 100
                job['opportunity_score'] = 90 + int((0.05 - percentile) * 200) # Scales 90-100
            elif percentile <= 0.20:
                # Next 15% -> 80 to 89
                job['opportunity_score'] = 80 + int(((0.20 - percentile) / 0.15) * 9)
            elif percentile <= 0.50:
                # Next 30% -> 70 to 79
                job['opportunity_score'] = 70 + int(((0.50 - percentile) / 0.30) * 9)
            else:
                # Bottom 50% -> scale 0 to 69 based on raw
                job['opportunity_score'] = int((job.get('raw_score', 0) / 100.0) * 69)
                
            # Update passed flag based on new threshold
            job['passed'] = job['opportunity_score'] >= self.threshold
            if not job['passed'] and not job['rejection_reason']:
                job['rejection_reason'] = "Normalized Score Below Threshold"
                
        return valid_jobs + rejects

if __name__ == "__main__":
    engine = MatchEngine()
    test_jobs = [
        ("Senior Backend Engineer", "Acme Corp", "Remote", "Need 8+ years experience in Java.", "500-1000 employees"),
        ("AI Product Manager", "OpenAI", "Remote", "Looking for GenAI product leaders.", "11-50 employees"),
        ("Associate Product Manager", "Groww", "Bangalore", "Entry level PM role.", "51-200 employees")
    ]
    
    for t, c, l, j, e in test_jobs:
        res = engine.evaluate(t, c, l, j, e)
        logger.info(f"[{res['opportunity_score']}] {t} @ {c} -> Passed: {res['passed']} {res['rejection_reason'] or ''}")
        logger.info("Why this Job:")
        logger.info(res["why_this_job"])
        logger.info("-" * 20)
