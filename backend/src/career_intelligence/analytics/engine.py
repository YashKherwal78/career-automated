from typing import List, Dict, Any
from collections import Counter
from src.discovery.jie.models import StructuredJob

class CareerAnalyticsEngine:
    @staticmethod
    def generate_job_market_insights(jobs: List[StructuredJob]) -> Dict[str, Any]:
        """Aggregates technology, skill, work mode, and salary distributions across structured job datasets."""
        total_jobs = len(jobs)
        if total_jobs == 0:
            return {}

        tech_counter = Counter()
        skill_counter = Counter()
        work_mode_counter = Counter()
        salary_sum = 0
        salary_count = 0

        for job in jobs:
            for tech in job.technologies:
                tech_counter[tech] += 1
            for skill in job.skills:
                skill_counter[skill] += 1
                
            work_mode_counter[job.work_mode] += 1
            
            # Sum yearly salary averages
            if job.salary.get("period") == "Yearly" and job.salary.get("minimum") is not None:
                salary_sum += job.salary["minimum"]
                salary_count += 1

        avg_salary = int(salary_sum / salary_count) if salary_count > 0 else 0

        return {
            "total_analyzed_jobs": total_jobs,
            "top_technologies": dict(tech_counter.most_common(10)),
            "top_skills": dict(skill_counter.most_common(10)),
            "work_mode_distribution": dict(work_mode_counter),
            "average_yearly_base_salary": avg_salary
        }
