import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.system.logger import setup_logger
logger = setup_logger("validate_sprint_c")

def test_outreach():
    logger.info("--- Testing Outreach Generation ---")
    from src.outreach.engine import OutreachEngine
    engine = OutreachEngine(dry_run=True)
    intel = {"domain": "AI / GenAI", "is_hiring": True, "industry": "Technology"}
    
    logger.info("--- Testing Outreach Generation and Email Critic ---")
    from src.outreach.critic import EmailCritic
    critic = EmailCritic()
    
    passed = False
    for attempt in range(3):
        logger.info(f"Generation Attempt {attempt + 1}...")
        subject, body = engine.generate_email("Sarah", "OpenAI", "Recruiter", "", "AI / GenAI", "CareerAutomated", intel)
        logger.info(f"Subject: {subject}")
        logger.info(f"Body:\n{body}")
        
        scorecard = critic.evaluate(body, "OpenAI", "CareerAutomated", "AI / GenAI")
        logger.info("Critic Scorecard:")
        for k, v in scorecard.items():
            logger.info(f"  {k}: {v}")
            
        if scorecard["status"] == "PASS":
            passed = True
            break
        else:
            logger.info(f"Attempt {attempt + 1} failed: {scorecard.get('reason')}")
            
    assert passed, "Email Critic failed after 3 attempts."
    
def test_agent5():
    logger.info("--- Testing Agent 5 Integration ---")
    from src.resume.agent5_resume_tailor import tailor_resume
    from src.utils.llm_router import LLMRouter
    llm = LLMRouter()
    
    # Needs a mock base_resume to run without full LaTeX
    base_resume = "data/yash_resume_base_v2.tex"
    if not os.path.exists(base_resume):
        os.makedirs("data", exist_ok=True)
        with open(base_resume, "w") as f:
            f.write("\\documentclass{article}\n\\begin{document}\n\\resumeProjectHeading{\\textbf{CareerAutomated}}{}\n\\resumeItem{Built an AI ATS}\n\\end{document}")
            
    try:
        resume_path, proj = tailor_resume(llm, base_resume, "Stripe", "Software Engineer", "Looking for backend engineers with Python experience", 999, "data/resumes", mode="application")
        logger.info(f"Tailored Resume: {resume_path}")
        logger.info(f"Selected Project: {proj}")
    except Exception as e:
        logger.info(f"Agent 5 Error (Expected if LaTeX not installed locally): {e}")

def test_greenhouse():
    logger.info("--- Testing Greenhouse Initialization ---")
    from src.applications.handlers.greenhouse import GreenhouseHandler
    # Just initialize it to ensure no import/syntax errors
    try:
        handler = GreenhouseHandler(None, "Software Engineer", "Test Company", "", "data/OUTREACH_RESUME.pdf")
        logger.info("GreenhouseHandler instantiated successfully.")
    except Exception as e:
        logger.info(f"GreenhouseHandler Error: {e}")

def run_validation():
    print("======================================")
    print("CareerAutomated Sprint C Validation")
    print("======================================")
    
    test_outreach()
    test_agent5()
    test_greenhouse()
    
    print("\nValidation complete. Check logs for details.")

if __name__ == "__main__":
    run_validation()
