from typing import Dict, Any, List, Tuple
from src.discovery.search_planner import SearchTask

class IntentFilter:
    """
    Lightweight, deterministic pre-ranking filter.
    Rejects obvious mismatches (Seniority, Role Family) before expensive ranking.
    """
    
    # Configurable global rejection lists based on experience profiles
    # 'manager' is explicitly excluded to allow 'Product Manager'
    EXPERIENCE_REJECT_MAP = {
        "Entry": ["senior", "staff", "principal", "lead", "director", "head", "vp", "chief", "founding senior"],
        "Associate": ["senior", "staff", "principal", "lead", "director", "head", "vp", "chief", "founding senior"]
    }
    
    # Configurable role family mappings
    ROLE_FAMILY_RULES = {
        "Product": {
            "allowed": ["product", "apm", "associate product", "product owner", "product analyst", "product operations"],
            "rejected": ["territory", "sales", "specification", "medical representative", "marketing", "developer"]
        },
        "Software": {
            "allowed": ["software", "developer", "engineer", "programmer", "coder", "sde"],
            "rejected": ["sales", "product manager", "marketing", "hr", "recruiter"]
        }
    }

    def __init__(self):
        # In a full production system, these dicts could be loaded from a YAML file.
        pass

    def filter_opportunities(self, opportunities: List[Dict[str, Any]], task: SearchTask) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Filters raw opportunities based on the SearchTask intent.
        Returns the filtered list of opportunities and the funnel metrics.
        """
        metrics = {
            "jobs_retrieved": len(opportunities),
            "jobs_passed": 0,
            "jobs_rejected_experience": 0,
            "jobs_rejected_role": 0
        }
        
        passed_jobs = []
        rejected_jobs = []
        
        # Determine active rejection keywords based on task experience profile
        exp_reject_keywords = set()
        for exp in task.experience_profile:
            if exp in self.EXPERIENCE_REJECT_MAP:
                exp_reject_keywords.update(self.EXPERIENCE_REJECT_MAP[exp])
                
        # Determine role family rules
        role_rules = self.ROLE_FAMILY_RULES.get(task.role_family, {"allowed": [], "rejected": []})
        role_reject_keywords = role_rules["rejected"]
        role_allow_keywords = role_rules["allowed"]

        for job in opportunities:
            title = job.get("title", job.get("positionName", "")).lower()
            if not title:
                # If no title, cautiously let it through to ranking, or drop it. 
                passed_jobs.append(job)
                continue
                
            # 1. Experience Rejection
            rejected_exp_word = None
            for word in exp_reject_keywords:
                if word in title:
                    rejected_exp_word = word
                    break
            
            if rejected_exp_word:
                metrics["jobs_rejected_experience"] += 1
                job["_rejection_reason"] = f"Rejected because: Senior keyword ({rejected_exp_word})"
                rejected_jobs.append(job)
                continue
                
            # 2. Role Family Rejection (Strict)
            rejected_role_word = None
            for word in role_reject_keywords:
                if word in title:
                    rejected_role_word = word
                    break
                    
            if rejected_role_word:
                metrics["jobs_rejected_role"] += 1
                job["_rejection_reason"] = f"Rejected because: Role mismatch ({rejected_role_word})"
                rejected_jobs.append(job)
                continue
                
            # 3. Require at least one Allowed Keyword (Strict Mode)
            if role_allow_keywords:
                matched_allow = False
                for word in role_allow_keywords:
                    if word in title:
                        matched_allow = True
                        break
                        
                if not matched_allow:
                    metrics["jobs_rejected_role"] += 1
                    job["_rejection_reason"] = f"Rejected because: Missing required role keyword (e.g., product)"
                    rejected_jobs.append(job)
                    continue
            
            # If it passed all filters
            passed_jobs.append(job)
            
        metrics["jobs_passed"] = len(passed_jobs)
        return passed_jobs, rejected_jobs, metrics
