import json
from ddgs import DDGS
from groq import Groq
from src.utils.llm_router import LLMRouter
from src.crm.database import add_or_update_lead, get_cached_intelligence, set_cached_intelligence

def calculate_priority_score(metadata: dict) -> int:
    score = 0
    domain = metadata.get("domain", "")
    emp_str = str(metadata.get("employee_count", ""))
    
    if "AI / GenAI" in domain: score += 3
    if "SaaS" in domain: score += 2
    if "Enterprise Software" in domain: score += 2
    if "Consulting" in domain: score -= 3
    if "IT Services" in domain: score -= 3
    if "Manufacturing" in domain: score -= 2
    if "Government" in domain: score -= 2
        
    if metadata.get("is_hiring", False): score += 2
    if metadata.get("founder_email"): score += 2
        
    try:
        nums = [int(s) for s in emp_str.replace(",", "").split() if s.isdigit()]
        if nums:
            count = nums[0]
            if count < 100: score += 2
            elif count < 500: score += 1
            elif count > 5000: score -= 2
    except:
        pass
        
    return score

def run_intelligence_engine(company_name: str) -> dict:
    cached = get_cached_intelligence(company_name)
    if cached:
        print(f"Using cached intelligence for {company_name}")
        return cached

    query_general = f"{company_name} company employee count industry domain hiring careers"
    results_general = DDGS().text(query_general, max_results=3)
    context_general = " ".join([r["body"] for r in results_general]) if results_general else "No generic info found."
    
    prompt = f"""
    You are a Recruiting Intelligence Agent. Based on the search results for the company '{company_name}', extract the following information.

    Search Context: {context_general}

    CLASSIFICATION INSTRUCTION:
    Map the company strictly to one of these domains: 
    "AI / GenAI", "SaaS", "Enterprise Software", "Analytics", "Healthcare", "FinTech", "EdTech", "Cloud", "Data Centers", "Industrial Automation", "Consulting", "Manufacturing", "Other"

    Return ONLY valid JSON matching this schema:
    {{
        "domain": "Classification from the list above",
        "employee_count": "e.g. 50-200 or null",
        "is_hiring": true/false
    }}
    """
    
    try:
        router = LLMRouter()
        response = router.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            intent="outreach"
        )
    except Exception as e:
        print(f"Error in intelligence engine (All keys failed) for {company_name}: {e}")
        return {"domain": "Other", "employee_count": None, "is_hiring": False, "priority_score": 0}
    try:
        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        metadata = json.loads(content)
        metadata["priority_score"] = calculate_priority_score(metadata)
        set_cached_intelligence(company_name, metadata)
        return metadata
    except Exception as e:
        print(f"Error parsing intelligence engine response for {company_name}: {e}")
        return {"domain": "Other", "employee_count": None, "is_hiring": False, "priority_score": 0}
