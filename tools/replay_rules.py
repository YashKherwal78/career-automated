import os
import json
import time
from collections import defaultdict
from src.crm.database import get_connection
from src.discovery.eligibility_engine import EligibilityEngine

def run_replay():
    print("Offline Rule Replay Engine")
    print("--------------------------")
    
    # 1. Fetch immutable historical jobs
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT raw_payload, eligibility_status, rule_version, matched_rule FROM opportunity_cache")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No historical opportunities found in cache.")
        return
        
    print(f"Loaded {len(rows)} historical opportunities from cache.")
    
    # 2. Instantiate current rule engine
    engine = EligibilityEngine()
    print(f"Loaded rule version: {engine.rule_version}")
    
    # 3. Replay in memory
    start_time = time.time()
    
    hist_eligible = 0
    hist_rejected = 0
    new_eligible = 0
    new_rejected = 0
    changed_decisions = 0
    
    new_rule_hits = defaultdict(int)
    
    for row in rows:
        raw_json, old_status, old_version, old_matched_rule = row
        opp = json.loads(raw_json)
        
        if old_status == "ELIGIBLE":
            hist_eligible += 1
        elif old_status == "REJECTED":
            hist_rejected += 1
            
        decision = engine.check_eligibility(opp)
        new_status = "ELIGIBLE" if decision.eligible else "REJECTED"
        
        if new_status == "ELIGIBLE":
            new_eligible += 1
        else:
            new_rejected += 1
            
        new_rule_hits[decision.matched_rule] += 1
            
        if old_status != new_status:
            changed_decisions += 1
            
    execution_time = time.time() - start_time
    
    # 4. Generate report
    report = [
        "# Rule Replay Validation Report",
        f"**Execution Time**: {execution_time:.3f} seconds",
        f"**Total Opportunities Replayed**: {len(rows)}",
        "",
        "## Historical Data (In Database)",
        f"- **Eligible**: {hist_eligible}",
        f"- **Rejected**: {hist_rejected}",
        "",
        f"## New Rules (Version: {engine.rule_version})",
        f"- **Eligible**: {new_eligible}",
        f"- **Rejected**: {new_rejected}",
        "",
        "## Comparison",
        f"- **Changed Decisions**: {changed_decisions}",
        f"- **Net Change in Eligible Queue**: {new_eligible - hist_eligible}",
        "",
        "## New Rule Hit Frequency"
    ]
    
    for rule, count in sorted(new_rule_hits.items(), key=lambda x: x[1], reverse=True):
        report.append(f"- **{rule}**: {count}")
        
    report_path = os.path.join(os.path.dirname(__file__), "..", "rule_replay_validation.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"\nReplay Complete in {execution_time:.3f}s")
    print(f"Changed Decisions: {changed_decisions}")
    print(f"Validation report saved to {report_path}")

if __name__ == "__main__":
    run_replay()
