import json
from src.config.config import Config
from groq import Groq
from src.crm.database import add_or_update_lead, get_lead

def run_job_matching(groq_client: Groq, company_name: str, job_id: int, job_description: str, days_old: int = 0) -> dict:
    """Agent 3: Job Matching & Probability Scoring"""
    print(f"Agent 3: Running Job Matching and Scoring for {company_name} (Job ID: {job_id})...")
    
    # Read resumes
    try:
        with open(str(Config.DATA_DIR / "yash_resume_aiml.tex"), "r") as f:
            ai_resume = f.read()
        with open(str(Config.DATA_DIR / "yash_resume_pm.tex"), "r") as f:
            pm_resume = f.read()
    except Exception as e:
        print(f"Error reading resumes: {e}")
        return {}
        
    prompt = f"""
    You are an expert Recruiting Intelligence Agent. 
    You must evaluate a candidate's fit for a specific job based on two different resume profiles.

    JOB DESCRIPTION:
    {job_description}

    JOB FRESHNESS:
    This job was posted {days_old} days ago. Jobs older than 14 days have significantly lower reply probabilities.

    EXPERIENCE FILTER INSTRUCTIONS:
    - You MUST heavily downrank or reject jobs that require: '3+ years', '5+ years', 'Senior', 'Lead', 'Principal', 'Staff', 'Manager', 'Director'.
    - You MUST prioritize and increase 'interview_probability' for jobs that mention: '0-1 years', 'Internship', 'Trainee', 'Graduate', 'Associate', 'Entry Level', 'Freshers', 'New Grad'.

    AI ENGINEER RESUME (ai_resume.tex):
    {ai_resume[:1500]} ... 

    PRODUCT MANAGER RESUME (product_resume.tex):
    {pm_resume[:1500]} ... 

    Your task is to:
    1. Score the AI Resume fit from 0-100.
    2. Score the Product Resume fit from 0-100.
    3. Determine the winning resume family ('AI Resume' or 'Product Resume').
    4. Calculate 'job_match_score' (overall fit).
    5. Calculate 'reply_probability' and 'interview_probability' (0-100%, considering days_old and match). 
       *CRITICAL*: Optimize for realistic interview_probability for a final-year IIT Roorkee student. Filter out high job-match scores if the seniority makes an interview impossible.
    6. Provide a 'recommendation_class' ("APPLY IMMEDIATELY", "APPLY THIS WEEK", "IGNORE") based on optimizing for interview_probability.
       - APPLY IMMEDIATELY: High priority (Full-Time Entry Level, New Grad, Associate, Internships).
       - APPLY THIS WEEK: Good fit but older or slightly less aligned.
       - IGNORE: Low interview probability (Senior, requires 3+ years experience, mismatch).
    7. Provide a 'confidence' float (0.0 to 1.0).
    8. Provide detailed 'reasoning' explaining the classification.

    Return ONLY valid JSON:
    {{
        "ai_resume_match_score": 90,
        "product_resume_match_score": 40,
        "job_match_score": 90,
        "recommended_resume_family": "AI Resume",
        "reply_probability": 45,
        "interview_probability": 20,
        "recommendation_class": "APPLY IMMEDIATELY",
        "confidence": 0.85,
        "reasoning": "High match for AI skills. Job is fresh. Excellent fit for New Grad."
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        
        # Store global agent metadata for explainability
        lead = get_lead(company_name)
        agent_metadata_str = lead.get("agent_metadata", "{}") if lead else "{}"
        try:
            agent_meta = json.loads(agent_metadata_str)
        except:
            agent_meta = {}
            
        agent_meta["job_matching"] = {
            "decision": data.get("decision"),
            "confidence": data.get("confidence"),
            "reasoning": data.get("reasoning")
        }
        
        # Save to database
        add_or_update_lead(company_name, {
            "job_match_score": data.get("job_match_score", 0),
            "resume_match_score": max(data.get("ai_resume_match_score", 0), data.get("product_resume_match_score", 0)),
            "resume_family": data.get("recommended_resume_family", "AI Resume"),
            "agent_metadata": json.dumps(agent_meta)
        })
        print(f"Agent 3 Complete! Winner: {data.get('recommended_resume_family')} (Interview Prob: {data.get('interview_probability')}%)")
        return data
    except Exception as e:
        print(f"Agent 3 Error: {e}")
        return {}

if __name__ == "__main__":
    client = Groq(api_key=Config.GROQ_API_KEY)
    run_job_matching(client, "Google", 1, "We are looking for an AI Engineer Intern to build Retrieval-Augmented Generation (RAG) pipelines...", days_old=3)
