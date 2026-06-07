import csv
from datetime import datetime
from typing import List, Dict
from src.jobs.providers.base_provider import JobProvider

class CSVProvider(JobProvider):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def discover_jobs(self) -> List[Dict]:
        jobs = []
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Provide defaults or transformations if needed
                    job = {
                        "company_name": row.get("company_name", ""),
                        "job_title": row.get("job_title", ""),
                        "job_url": row.get("job_url", ""),
                        "job_description": row.get("job_description", ""),
                        "location": row.get("location", ""),
                        "experience_required": row.get("experience_required", ""),
                        "skills_required": row.get("skills_required", ""),
                        "employment_type": row.get("employment_type", ""),
                        "posting_date": row.get("posting_date", datetime.now().isoformat()),
                        "days_old": int(row.get("days_old", 0))
                    }
                    jobs.append(job)
        except Exception as e:
            print(f"Error reading from CSV provider: {e}")
        return jobs
