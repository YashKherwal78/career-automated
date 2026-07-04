import re

class EligibilityFilter:
    @staticmethod
    def check_eligibility(job_location: str, job_description: str, profile_manager) -> dict:
        """
        Determines if a job should be skipped BEFORE launching the browser.
        Returns: {"is_eligible": bool, "skip_reason": str}
        """
        if not job_location:
            job_location = ""
        if not job_description:
            job_description = ""
            
        loc_lower = str(job_location).lower()
        desc_lower = str(job_description).lower()
        
        # 1. Strict Authorization & Clearance Check
        auth_keywords = [
            "us work authorization required",
            "must be a us citizen",
            "must be a u.s. citizen",
            "security clearance required",
            "active clearance",
            "top secret clearance",
            "green card holder",
            "no sponsorship available",
            "no visa sponsorship",
            "we do not sponsor",
            "cannot provide sponsorship",
            "do not provide sponsorship",
            "without sponsorship",
            "without employer sponsorship"
        ]
        
        for kw in auth_keywords:
            if kw in desc_lower or kw in loc_lower:
                return {
                    "is_eligible": False,
                    "skip_reason": f"Failed Authorization Check: contains strict keyword '{kw}'"
                }

        # 2. US-Only Location Check
        # If the location is strictly in the US and doesn't explicitly support Remote/Global/Relocation/Sponsorship
        us_state_abbrevs = [" al,", " ak,", " az,", " ar,", " ca,", " co,", " ct,", " de,", " fl,", " ga,", " hi,", " id,", " il,", " in,", " ia,", " ks,", " ky,", " la,", " me,", " md,", " ma,", " mi,", " mn,", " ms,", " mo,", " mt,", " ne,", " nv,", " nh,", " nj,", " nm,", " ny,", " nc,", " nd,", " oh,", " ok,", " or,", " pa,", " ri,", " sc,", " sd,", " tn,", " tx,", " ut,", " vt,", " va,", " wa,", " wv,", " wi,", " wy,"]
        us_keywords = ["united states", "usa", "us - "]
        
        is_us_location = False
        
        # Check standard US keywords
        if any(kw in loc_lower for kw in us_keywords):
            is_us_location = True
            
        # Check state abbreviations (e.g. "San Francisco, CA")
        loc_comma = loc_lower + "," # To catch abbreviation at end of string
        if any(state in loc_comma for state in us_state_abbrevs):
            is_us_location = True

        if is_us_location:
            # Check for saving graces (Remote, Global, Relocation, Visa Sponsorship)
            saving_graces = [
                "remote", 
                "anywhere", 
                "worldwide", 
                "global", 
                "relocation support", 
                "relocation assistance", 
                "visa sponsorship",
                "h1b",
                "india",
                "uk",
                "canada"
            ]
            
            has_saving_grace = False
            for grace in saving_graces:
                if grace in loc_lower or grace in desc_lower:
                    has_saving_grace = True
                    break
                    
            if not has_saving_grace:
                return {
                    "is_eligible": False,
                    "skip_reason": "Failed Location Check: US-only role with no remote/relocation/sponsorship support"
                }
                
        return {
            "is_eligible": True,
            "skip_reason": ""
        }
