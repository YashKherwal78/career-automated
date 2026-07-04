from typing import Dict, Tuple

def score_contact(contact: Dict, profile_data: Dict, job_title: str) -> Tuple[int, str]:
    """
    Phase 3 - Referral Scoring
    IIT Roorkee: +100
    Other IIT: +80
    Hiring Manager: +60
    Recruiter: +40
    Technical Engineer: +30
    Role Relevant To Job: +30
    """
    score = 0
    reasons = []
    
    # 1. Education
    education = profile_data.get("education", "").lower()
    if "iit roorkee" in education or "indian institute of technology roorkee" in education:
        score += 100
        reasons.append("IIT Roorkee Alumni (+100)")
    elif "iit" in education or "indian institute of technology" in education:
        score += 80
        reasons.append("IIT Alumni (+80)")
        
    # 2. Authority
    c_type = contact.get("contact_type", "")
    if c_type == "Hiring Manager":
        score += 60
        reasons.append("Hiring Manager (+60)")
    elif c_type == "Recruiter":
        score += 40
        reasons.append("Recruiter (+40)")
    elif c_type == "Technical IC":
        score += 30
        reasons.append("Technical Engineer (+30)")
        
    # 3. Role Relevance
    # Simple keyword match between contact's title and the job we are applying to
    contact_title_lower = contact.get("job_title", "").lower()
    job_title_lower = job_title.lower()
    
    # Split titles into words and find overlap
    job_words = set([w for w in job_title_lower.split() if len(w) > 3])
    contact_words = set([w for w in contact_title_lower.split() if len(w) > 3])
    
    if len(job_words.intersection(contact_words)) > 0:
        score += 30
        reasons.append("Role Relevant to Job (+30)")
        
    ranking_reason = ", ".join(reasons) if reasons else "No specific pedigree signals found."
    
    return score, ranking_reason
