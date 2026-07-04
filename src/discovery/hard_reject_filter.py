from typing import Dict, Any, List, Tuple
from src.discovery.search_planner import SearchTask

class HardRejectFilter:
    """
    Evaluates opportunities against absolute dealbreakers (e.g. Visa required, 8+ YOE, wrong country).
    Drops these jobs instantly before scoring.
    """
    def __init__(self):
        pass

    def filter_opportunities(self, opportunities: List[Dict[str, Any]], task: SearchTask) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        metrics = {
            "jobs_evaluated": len(opportunities),
            "jobs_passed": 0,
            "jobs_hard_rejected": 0
        }
        
        passed_jobs = []
        rejected_jobs = []

        # Convert task locations to lowercase for easy matching
        target_countries = [loc.split(",")[-1].strip().lower() for loc in task.locations] if task.locations else ["india"]

        for job in opportunities:
            rejected_reason = None
            
            # 1. Location Mismatch (Different Country)
            job_location = job.get("location", job.get("jobLocation", "")).lower()
            if job_location and job_location != "remote":
                country_match = False
                for tc in target_countries:
                    if tc in job_location:
                        country_match = True
                        break
                
                # Comprehensive list of Indian states and Tier 1/2 cities
                indian_locations = [
                    "andhra pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana",
                    "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", 
                    "odisha", "punjab", "rajasthan", "tamil nadu", "telangana", "uttar pradesh", "uttarakhand", 
                    "west bengal", "delhi", "ncr", "chandigarh",
                    "bangalore", "bengaluru", "mumbai", "pune", "hyderabad", "chennai", "kolkata", "ahmedabad", 
                    "surat", "jaipur", "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal", "visakhapatnam", 
                    "patna", "vadodara", "ghaziabad", "agra", "nashik", "faridabad", "meerut", "rajkot", "varanasi", 
                    "aurangabad", "amritsar", "navi mumbai", "ranchi", "coimbatore", "vijayawada", "jodhpur", 
                    "madurai", "raipur", "kota", "guwahati", "mysore", "mysuru", "gurgaon", "gurugram", "noida", 
                    "thiruvananthapuram", "trivandrum", "kochi", "cochin", "bhubaneswar", "dehradun"
                ]
                if not country_match and "india" in target_countries:
                    if any(loc in job_location for loc in indian_locations):
                        country_match = True
                
                if not country_match and "remote" not in job_location:
                    rejected_reason = f"Hard Reject: Location mismatch ({job_location} not in {target_countries})"
            if "candidate_fit" in job:
                fit = job["candidate_fit"]
                if not fit.get("experience", {}).get("fit", True):
                    # Reject if experience fit is strictly False
                    rejected_reason = fit["experience"].get("reason", "Experience mismatch.")
                
                elif job.get("jie", {}).get("employment_type") == "Internship" and "Internship" not in task.experience_profile:
                    rejected_reason = "Hard Reject: Internship only (disabled in profile)"
                elif job.get("jie", {}).get("employment_type") == "Contract" and "Contract" not in task.employment_types:
                    rejected_reason = "Hard Reject: Contract role (excluded)"
            else:
                # Fallback to title strings if no JIE present
                title = job.get("title", job.get("positionName", "")).lower()
                if "internship" in title and "Internship" not in task.experience_profile:
                    rejected_reason = "Hard Reject: Internship only (disabled in profile)"
                elif "contract" in title and "Contract" not in task.employment_types:
                    rejected_reason = "Hard Reject: Contract role (excluded)"

            if rejected_reason:
                job["_rejection_reason"] = rejected_reason
                rejected_jobs.append(job)
                metrics["jobs_hard_rejected"] += 1
            else:
                passed_jobs.append(job)

        metrics["jobs_passed"] = len(passed_jobs)
        return passed_jobs, rejected_jobs, metrics
