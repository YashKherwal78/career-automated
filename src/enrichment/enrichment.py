from abc import ABC, abstractmethod
import requests
from src.config.config import Config
from src.crm.database import get_lead, add_or_update_lead
from datetime import datetime
import json
import re

class EnrichmentProvider(ABC):
    @abstractmethod
    def enrich_domain(self, domain_url: str) -> dict:
        """Returns standard dict of role to email"""
        pass

class HunterProvider(EnrichmentProvider):
    def __init__(self):
        self.api_key = Config.HUNTER_API_KEY
        
    def enrich_domain(self, domain_url: str) -> dict:
        if not self.api_key:
            return {}
        print(f"[HunterProvider] Searching for {domain_url}...")
        url = f"https://api.hunter.io/v2/domain-search?domain={domain_url}&api_key={self.api_key}"
        result = {}
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json().get("data", {})
                emails = data.get("emails", [])
                
                for email in emails:
                    position = (email.get("position") or "").lower()
                    val = email.get("value")
                    
                    if "founder" in position or "ceo" in position:
                        result["founder_email"] = val
                    elif "cto" in position or "chief technology" in position:
                        result["cto_email"] = val
                    elif "hiring" in position or "talent" in position or "acquisition" in position:
                        result["hiring_manager_email"] = val
                    elif "recruiter" in position:
                        result["recruiter_email"] = val
                    elif "hr" in position or "human resources" in position:
                        result["hr_email"] = val
        except Exception as e:
            print(f"[HunterProvider] Error: {e}")
        return result

class GetProspectProvider(EnrichmentProvider):
    def __init__(self):
        self.api_key = Config.GETPROSPECT_API_KEY
        
    def enrich_domain(self, domain_url: str) -> dict:
        return {} # Fallback to Hunter for now

def _determine_company_size(employee_count_str: str) -> str:
    if not employee_count_str:
        return "Startup"
    try:
        nums = [int(s) for s in re.findall(r'\d+', employee_count_str.replace(",", ""))]
        if nums and max(nums) >= 500:
            return "Enterprise"
    except:
        pass
    return "Startup"

def enrich_company(company_name: str, domain_url: str = None) -> dict:
    lead = get_lead(company_name)
    if lead and lead.get("last_enriched_date"):
        try:
            last_date = datetime.fromisoformat(lead["last_enriched_date"])
            if (datetime.now() - last_date).days < 30:
                print(f"[{company_name}] Enrichment Cached. Skipping API call.")
                return dict(lead)
        except:
            pass

    if not domain_url:
        domain_url = f"{company_name.lower().replace(' ', '')}.com"

    providers = [GetProspectProvider(), HunterProvider()]
    
    enrichment_result = {
        "founder_email": None,
        "cto_email": None,
        "hiring_manager_email": None,
        "recruiter_email": None,
        "hr_email": None,
        "contact_confidence": 0.0,
        "enrichment_source": "None"
    }
    
    for provider in providers:
        res = provider.enrich_domain(domain_url)
        if res:
            enrichment_result.update(res)
            enrichment_result["contact_confidence"] = 0.8
            enrichment_result["enrichment_source"] = provider.__class__.__name__
            break
            
    enrichment_result["last_enriched_date"] = datetime.now().isoformat()
    if enrichment_result["enrichment_source"] != "None":
        enrichment_result["enrichment_cost"] = 0.05
        
    # Implement Contact Priority Ranking
    emp_count = lead.get("employee_count", "") if lead else ""
    company_type = _determine_company_size(emp_count)
    
    target_email = None
    target_role = None
    
    if company_type == "Startup":
        # Startup: Founder > CTO > Hiring Manager > HR
        priorities = [
            ("founder_email", "Founder"),
            ("cto_email", "CTO"),
            ("hiring_manager_email", "Hiring Manager"),
            ("hr_email", "HR")
        ]
    else:
        # Enterprise: Hiring Manager > Recruiter > HR > Founder
        priorities = [
            ("hiring_manager_email", "Hiring Manager"),
            ("recruiter_email", "Recruiter"),
            ("hr_email", "HR"),
            ("founder_email", "Founder")
        ]
        
    for key, role_name in priorities:
        if enrichment_result.get(key):
            target_email = enrichment_result[key]
            target_role = role_name
            break
            
    enrichment_result["target_email"] = target_email
    enrichment_result["target_role"] = target_role
    
    # Store Agent Explainability for Enrichment
    enrichment_result["decision"] = target_email
    enrichment_result["confidence"] = enrichment_result["contact_confidence"]
    enrichment_result["reasoning"] = f"Company classified as {company_type}. Priority resolved to {target_role}."

    # Update global agent metadata in DB
    agent_metadata_str = lead.get("agent_metadata", "{}") if lead else "{}"
    try:
        agent_meta = json.loads(agent_metadata_str)
    except:
        agent_meta = {}
    agent_meta["enrichment"] = {
        "decision": target_email,
        "confidence": enrichment_result["confidence"],
        "reasoning": enrichment_result["reasoning"]
    }
    enrichment_result["agent_metadata"] = json.dumps(agent_meta)

    add_or_update_lead(company_name, enrichment_result)
    return enrichment_result
