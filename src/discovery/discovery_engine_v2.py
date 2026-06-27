from typing import List, Dict, Tuple
from src.discovery.providers.provider_manager import ProviderManager
from src.discovery.eligibility_engine import EligibilityEngine
from src.applications.match_engine import MatchEngine
from src.discovery.normalization.experience_normalizer import ExperienceNormalizer
from src.discovery.ats_detector import ATSDetector
from src.discovery.priority_scheduler import PriorityScheduler

class DiscoveryEngineV2:
    def __init__(self):
        self.provider_manager = ProviderManager()
        self.eligibility_engine = EligibilityEngine()
        self.match_engine = MatchEngine()
        self.experience_normalizer = ExperienceNormalizer()
        self.ats_detector = ATSDetector()
        self.scheduler = PriorityScheduler()
        
    def run_discovery(self, last_sync_timestamps: dict = None) -> Tuple[List[dict], dict]:
        print("DiscoveryEngineV2: Starting Fast Loop Job Discovery...")
        
        # 1. Get Scheduled Companies
        scheduled_companies = self.scheduler.get_companies_to_scan(limit=50)
        print(f"Scheduled {len(scheduled_companies)} high-priority companies for scan.")
        
        # 2. Run all health-checked providers, but restrict to scheduled companies
        # Assuming ProviderManager can be updated to accept `target_companies`.
        all_jobs = self.provider_manager.run_all_providers(last_sync_timestamps, target_companies=scheduled_companies)
        
        # 2. Deduplicate
        unique_jobs = {}
        duplicates_removed = 0
        for job in all_jobs:
            # V2 deduplication key
            key = f"{job.company}_{job.role}_{job.ats_type}".lower().strip()
            if key not in unique_jobs:
                unique_jobs[key] = job
            else:
                duplicates_removed += 1
                
        jobs_to_process = list(unique_jobs.values())
        print(f"Discovered {len(all_jobs)} jobs. Deduplicated down to {len(jobs_to_process)}.")
        
        # 3. Eligibility Filter & 4. Match Score
        final_jobs = []
        filtered_count = 0
        
        for job in jobs_to_process:
            # V3 Normalization
            normalized_exp = self.experience_normalizer.normalize(job.experience_required, job.role)
            job.experience_required = normalized_exp
            
            opp_dict = {
                "company": job.company,
                "role": job.role,
                "location": job.location,
                "remote_hybrid_onsite": job.remote_hybrid_onsite,
                "experience_required": job.experience_required,
                "skills": job.skills,
                "job_description": job.job_description,
                "ats_type": job.ats_type,
                "application_url": job.application_url,
                "source": job.source,
                "date_posted": job.date_posted
            }
            
            decision = self.eligibility_engine.check_eligibility(opp_dict)
            if not decision.eligible:
                filtered_count += 1
                continue
                
            score_data = self.match_engine.evaluate(
                job_title=job.role,
                company=job.company,
                location=job.location,
                job_description=job.job_description,
                employee_count=""
            )
            
            opp_dict["overall_score"] = score_data.get("overall_score", 0)
            opp_dict["reasoning"] = score_data.get("reasoning", "")
            
            final_jobs.append(opp_dict)
            
        # 5. Sort by score
        final_jobs.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        
        stats = {
            "total_found": len(all_jobs),
            "deduplicated": len(jobs_to_process),
            "duplicates_removed": duplicates_removed,
            "filtered": filtered_count,
            "final": len(final_jobs)
        }
        
        return final_jobs, stats
        
    def get_health_report(self) -> str:
        return self.provider_manager.get_health_report()
