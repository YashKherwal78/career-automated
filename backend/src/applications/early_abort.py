import re

class EarlyEligibilityScanner:
    def __init__(self, profile_manager=None):
        self.profile = profile_manager

    def scan_page(self, page_text: str) -> dict:
        text = page_text.lower()
        
        # 1. HARD REJECT CONDITIONS (SKIPPED_INELIGIBLE)
        hard_rejects = [
            (r"(must be authorized to work in|require authorization to work in|only accepting applications from|must have work authorization in)\s*(the\s*)?(us|u\.s\.|united states)", "US Work Authorization Required"),
            (r"(no|not providing|unable to provide)\s*(visa\s*)?sponsorship", "No Sponsorship Available"),
            (r"us only|u\.s\. only|united states only", "US Only Location"),
            (r"uk only|u\.k\. only|united kingdom only", "UK Only Location"),
            (r"singapore only", "Singapore Only Location"),
            (r"must graduate in (2027|2028|2029)", "Future Graduation Required"),
            (r"expected graduation (in|after) (2027|2028|2029)", "Future Graduation Required"),
            (r"current (university|college)\s*student(s)? required", "Current Student Required"),
            (r"currently enrolled in a(n)? (bachelor|master|phd)", "Current Student Required"),
            (r"([3-9]|[1-9][0-9])\+?\s*years\s*(of)?\s*(industry\s*)?experience\s*required", "Minimum Experience >= 3 Years"),
            (r"minimum (of\s*)?([3-9]|[1-9][0-9])\s*years", "Minimum Experience >= 3 Years"),
            (r"\b(senior|staff|principal)\b.*(only|required)", "Senior/Staff/Principal Level Only")
        ]
        
        for pattern, reason in hard_rejects:
            if re.search(pattern, text):
                return {"status": "SKIPPED_INELIGIBLE", "reason": reason}

        # 2. REVIEW CONDITIONS (REVIEW)
        review_conditions = [
            (r"([2-9])\+?\s*years\s*(of)?\s*experience\s*preferred", "2+ Years Experience Preferred"),
            (r"preferred graduation date", "Preferred Graduation Date Mentioned"),
            (r"(nice to have|preferred)\s*.*work authorization", "Work Authorization Preferred")
        ]
        
        for pattern, reason in review_conditions:
            if re.search(pattern, text):
                return {"status": "REVIEW", "reason": reason}

        # 3. ALLOW CONDITIONS (OK)
        # We don't strictly require these to be present to return OK, but if they are present, it's a strong OK.
        # By default, if no hard reject or review conditions match, we return OK.
        
        return {"status": "OK", "reason": "No hard constraints found"}
