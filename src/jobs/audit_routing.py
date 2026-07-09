from src.system.logger import setup_logger
logger = setup_logger('audit_routing')
from src.jobs.ranking import rank_job
from src.config.config import Config

def audit_routing():
    test_roles = [
        "Business Associate - Growth(Engagement)",
        "Product Operations Specialist",
        "Business Analyst",
        "AI Engineer",
        "Machine Learning Intern",
        "Software Development Engineer II"
    ]
    
    logger.info("="*60)
    logger.info("RESUME ROUTING AUDIT")
    logger.info("="*60)
    
    for role in test_roles:
        # Dummy job description
        job_data = {
            "job_title": role,
            "description": "Standard job description.",
            "company_name": "TestCorp"
        }
        
        result = rank_job(job_data)
        
        # We need to print Job Title, Resume Scores, Profile Scores, Selected Resume, Selected Profile, Routing Reason.
        # The rank_job function sets "recommended_resume" and "resume_confidence", but wait, "Profile Scores" are not part of rank_job.
        # Wait, the prompt says "Print: Job Title, Resume Scores, Profile Scores, Selected Resume, Selected Profile, Routing Reason"
        # Profile is selected in `src/applications/engine.py` using `_map_resume_to_profile`.
        
        recommended_resume = result.get("recommended_resume", "UNKNOWN")
        confidence = result.get("resume_confidence", 0)
        reasons = result.get("reasons", [])
        
        if "PRODUCT" in recommended_resume:
            profile = "BUSINESS_PROFILE / PM_PROFILE"
            resume_file = "Resume_prod.pdf"
        elif "AIML" in recommended_resume:
            profile = "AI_PROFILE"
            resume_file = "Resume_aiml.pdf"
        else:
            profile = "UNKNOWN"
            resume_file = "UNKNOWN"
            
        logger.info(f"\nJob Title:      {role}")
        logger.info(f"Routing Reason: {', '.join(reasons)}")
        logger.info(f"Resume Scores:  Confidence: {confidence}")
        logger.info(f"Selected Resume:{resume_file} ({recommended_resume})")
        logger.info(f"Select Profile: {profile}")
        logger.info("-"*60)

if __name__ == "__main__":
    audit_routing()
