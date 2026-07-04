import json
from src.config.config import Config
from groq import Groq
from src.crm.database import add_or_update_lead, get_lead

def generate_email_strategy(groq_client: Groq, company_name: str, job_description: str, selected_project: str) -> dict:
    """Agent 7: Determines the email strategy before writing the actual email."""
    print(f"Agent 7: Generating Email Strategy for {company_name}...")
    
    try:
        with open(Config.DATA_DIR / "context" / "yash_master_profile.md", "r") as f:
            yash_master_profile = f.read()
        context_str = f"\n\n--- YASH MASTER PROFILE ---\n{yash_master_profile}"
    except Exception:
        context_str = ""

    prompt = f"""
    You are an Email Strategy Agent.
    Before writing an email to a recruiter for the company '{company_name}', you must formulate the logical reasoning for the outreach.
    {context_str}
    
    JOB DESCRIPTION:
    {job_description}
    
    SELECTED PROJECT:
    {selected_project}
    
    Answer the following questions concisely:
    1. Why is this company a strong match?
    2. Why is this role a strong match?
    3. Why was this specific project selected to highlight?
    
    Return ONLY valid JSON matching this schema:
    {{
        "company_match_reasoning": "...",
        "role_match_reasoning": "...",
        "project_match_reasoning": "...",
        "decision": "Generated Strategy",
        "confidence": 0.85,
        "reasoning": "The strategy was selected because..."
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        strategy = json.loads(response.choices[0].message.content)
        
        # Log to CRM including agent_metadata
        lead = get_lead(company_name)
        agent_metadata_str = lead.get("agent_metadata", "{}") if lead else "{}"
        try:
            agent_meta = json.loads(agent_metadata_str)
        except:
            agent_meta = {}
            
        agent_meta["email_strategy"] = {
            "decision": strategy.get("decision"),
            "confidence": strategy.get("confidence"),
            "reasoning": strategy.get("reasoning")
        }
        
        add_or_update_lead(company_name, {
            "skill_gap_analysis": json.dumps(strategy), 
            "agent_metadata": json.dumps(agent_meta)
        }) 
        return strategy
    except Exception as e:
        print(f"Agent 7 Error: {e}")
        return {}

if __name__ == "__main__":
    client = Groq(api_key=Config.GROQ_API_KEY)
    print(generate_email_strategy(client, "Google", "AI Engineer Intern...", "Hybrid RAG Retrieval System"))
