import re
from typing import Dict, Any

class EligibilityDecision:
    def __init__(self, eligible: bool, reason: str):
        self.eligible = eligible
        self.reason = reason

class EligibilityEngine:
    """
    Deterministic V2 rule-based bouncer.
    Determines if an opportunity is ELIGIBLE or REJECTED.
    """
    def __init__(self):
        self.senior_keywords = ["senior", "staff", "principal", "lead", "director"]
        self.intern_keywords = ["intern", "internship"]
        self.supported_countries = ["india", "remote", "us", "united states"]

    def check_eligibility(self, opp: dict) -> EligibilityDecision:
        title_lower = str(opp.get("role", "")).lower()
        desc_lower = str(opp.get("job_description", "")).lower()
        exp_lower = str(opp.get("experience_required", "")).lower()
        loc_lower = str(opp.get("location", "")).lower()
        url = opp.get("application_url", "")

        # 1. Missing application URL
        if not url:
            return EligibilityDecision(False, "Missing Application URL")

        # 2. Senior / Staff / Principal
        if any(kw in title_lower for kw in self.senior_keywords):
            return EligibilityDecision(False, "Senior Role Detected")

        # 3. Internship (Hard rejected by default in V2)
        if any(kw in title_lower for kw in self.intern_keywords):
            return EligibilityDecision(False, "Internship Role Detected")

        # 4. Experience > 2 years
        # Catch explicit strings like "3+ years", "3 years", "5+ years", etc.
        exp_matches = re.findall(r'(\d+)\+?\s*years?', desc_lower + " " + exp_lower)
        for exp_str in exp_matches:
            if int(exp_str) > 2:
                return EligibilityDecision(False, f"Experience Requirement > 2 Years ({exp_str} years)")

        # 5. Country unsupported
        loc_supported = False
        for c in self.supported_countries:
            if c in loc_lower:
                loc_supported = True
                break
        
        # We'll be lenient if location is empty or just a city we don't explicitly reject
        if loc_lower and not loc_supported and ("uk" in loc_lower or "london" in loc_lower or "canada" in loc_lower or "europe" in loc_lower):
            return EligibilityDecision(False, "Unsupported Country")

        return EligibilityDecision(True, "Allowed")
