import json
from ddgs import DDGS
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

def collect_company_metadata(groq_client: Groq, company_name: str) -> dict:
    """Uses DDG search to attempt to find company domain, employee count, and CTO/Founder details."""
    
    # 1. Search for generic info
    query_general = f"{company_name} company employee count industry domain"
    results_general = DDGS().text(query_general, max_results=3)
    context_general = " ".join([r["body"] for r in results_general]) if results_general else "No generic info found."
    
    # 2. Search for Founders/CTO
    query_people = f"{company_name} CEO Founder CTO email contact"
    results_people = DDGS().text(query_people, max_results=3)
    context_people = " ".join([r["body"] for r in results_people]) if results_people else "No people info found."

    prompt = f"""
    You are an expert data researcher. Based on the following search results for the company '{company_name}', extract the following information.
    If you cannot find a piece of information, return null for it. DO NOT hallucinate emails. If an email is not explicitly in the text, guess the most likely format (e.g. first.last@companydomain.com) ONLY if you know the person's name and the company domain. If you do guess, mark it clearly or just return null if unsure.

    Search Context 1 (General):
    {context_general}

    Search Context 2 (People):
    {context_people}

    Return ONLY valid JSON matching this schema:
    {{
        "domain": "e.g. AI / SaaS / FinTech",
        "employee_count": "e.g. 50-200",
        "founder_name": "name or null",
        "founder_role": "CEO/Founder/etc or null",
        "founder_email": "email or null",
        "cto_name": "name or null",
        "cto_email": "email or null"
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        # parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error extracting metadata for {company_name}: {e}")
        return {}

if __name__ == "__main__":
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    res = collect_company_metadata(client, "OpenAI")
    print(json.dumps(res, indent=2))
