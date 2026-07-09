import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.crm.db_init import init_db
init_db()

from src.intelligence.intelligence import run_intelligence_engine
from src.intelligence.project_selector import ProjectSelector
import pandas as pd

def run_validation():
    companies = ["OpenAI", "Stripe", "Tesla", "TikTok", "Palantir"]
    
    results = []
    
    for comp in companies:
        print(f"Analyzing {comp}...")
        intel = run_intelligence_engine(comp)
        domain = intel.get("domain", "Unknown")
        project, rejected, reason, conf = ProjectSelector.select(comp, intel)
        
        results.append({
            "Company": comp,
            "Domain": domain,
            "Selected Project": project,
            "Rejected Project": rejected[0] if rejected else "None",
            "Reason": reason,
            "Confidence": conf
        })
        
    df = pd.DataFrame(results)
    
    print("\n======================================")
    print("Project Selector Validation Report")
    print("======================================")
    
    for r in results:
        print(f"Company: {r['Company']}")
        print(f"Detected Domain: {r['Domain']}")
        print(f"Selected Project: {r['Selected Project']}")
        print(f"Rejected Project: {r['Rejected Project']}")
        print(f"Reason: {r['Reason']}")
        print(f"Confidence: {r['Confidence']}")
        print("-" * 30)

if __name__ == "__main__":
    run_validation()
