import json
from src.outreach.engine import OutreachEngine
from src.outreach.prompts import HR_SYSTEM_PROMPT

def run_trace():
    print("--- OUTREACH ENGINE TRACE AUDIT ---\n")
    engine = OutreachEngine(dry_run=True)
    
    company = "Google"
    role = "Software Engineer"
    recruiter_name = "Jane Doe"
    notes = ""
    
    print("Is the Project Selection Engine being called? NO (Hardcoded empty in V1)")
    print("Is Candidate Intelligence Database being injected? YES (self.yash_profile and self.projects)")
    print("Is Email Critic being called? NO (V1 does not use critic)")
    print("Is Networking Outreach Prompt being used? NO (Using HR_SYSTEM_PROMPT)")
    print("\n--------------------------------------------------\n")
    
    prompt = f"""
        {HR_SYSTEM_PROMPT}
        
        Recruiter Name: {recruiter_name}
        Company: {company}
        Role: {role}
        Additional Notes: {notes}
        
        Candidate Profile Context:
        {engine.yash_profile}
        
        Projects:
        {engine.projects}
        
        Generate the email. Ensure it strictly meets all constraints. Target 75-150 words.
        """
        
    print(f"Company: {company}")
    print(f"Selected Project: NONE (V1 does not route)")
    print(f"Resume Selected: NONE (V1 does not attach resumes)")
    print(f"Prompt Used: HR_SYSTEM_PROMPT")
    print(f"Prompt File Path: src/outreach/prompts.py")
    print(f"Generator Used: llama-3.1-8b-instant")
    print(f"Critic Used: NONE")
    
    print("\n--- FINAL EMAIL ---")
    try:
        response = engine.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        print(f"Subject: {data.get('subject')}")
        print(f"Body:\n{data.get('body')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_trace()
