from typing import Dict, Any, List

class ApplicationPrioritizer:
    """
    Evaluates opportunities relative to one another to produce the daily application queue.
    Enforces sorting, tie-breaking, and diversity rules.
    """
    
    def __init__(self, max_per_company: int = 3, queue_size: int = 50):
        self.max_per_company = max_per_company
        self.queue_size = queue_size

    def prioritize_queue(self, scored_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1. Initial sorting
        # Primary: Final Score
        # Secondary: Confidence Score
        # Tertiary: Official ATS preference
        def sort_key(job):
            res = job.get("match_result")
            if not res:
                return (0, 0.0, 0)
                
            is_ats = 1 if job.get("source") == "PipelineA_ATS" else 0
            
            return (
                res.final_score,
                res.confidence,
                is_ats
            )
            
        scored_jobs.sort(key=sort_key, reverse=True)
        
        # 2. Enforce Diversity & Build Queue
        final_queue = []
        company_counts = {}
        
        for job in scored_jobs:
            if len(final_queue) >= self.queue_size:
                break
                
            res = job.get("match_result")
            if not res:
                continue
                
            company = job.get("company", job.get("companyName", "Unknown")).strip().lower()
            
            # Check company diversity limit
            if company_counts.get(company, 0) >= self.max_per_company:
                continue
                
            # Valid job, add to queue
            company_counts[company] = company_counts.get(company, 0) + 1
            
            # 3. Decorate with final queue metadata
            rank = len(final_queue) + 1
            
            job["queue_metadata"] = {
                "rank": rank,
                "recommendation": res.recommendation,
                "final_score": res.final_score,
                "confidence": res.confidence,
                "reason": f"Rank #{rank} opportunity based on score and diversity filters."
            }
            
            final_queue.append(job)
            
        return final_queue
