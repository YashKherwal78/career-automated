from abc import ABC, abstractmethod
import time
from typing import List, Dict, Any
from src.discovery.models import RawJob, CanonicalJob, JobIdentity
import hashlib

class JobNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        pass

    def _generate_fingerprint(self, company_id: str, title: str, location: str, emp_type: str) -> str:
        key = f"{company_id}_{title}_{location}_{emp_type}".lower()
        return hashlib.md5(key.encode()).hexdigest()

class GreenhouseNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.board_identity.board_token if hasattr(raw_job.board_identity, 'board_token') else "unknown"
        
        job_list = raw_job.payload.get("jobs", []) if "jobs" in raw_job.payload else [raw_job.payload]
        for job in job_list:
            dept_name = job.get("departments", [{}])[0].get("name", "") if job.get("departments") else ""
            external_id = str(job.get("id", ""))
            title = job.get("title", "")
            location = job.get("location", {}).get("name", "")
            
            emp_type = ""
            remote = ""
            if location and "remote" in location.lower():
                remote = "Remote"
            
            identity = JobIdentity(
                provider="greenhouse",
                board_id=company_id,
                external_job_id=external_id
            )
            
            jobs.append(CanonicalJob(
                identity=identity,
                company_id=company_id,
                board_id=company_id,
                title=title,
                description="",
                location=location,
                remote_type=remote,
                department=dept_name,
                employment_type=emp_type,
                seniority="",
                salary_min=None,
                salary_max=None,
                salary_currency="",
                posted_at=job.get("updated_at", ""),
                apply_url=job.get("absolute_url", ""),
                raw_payload=job,
                normalized_at=time.time()
            ))
        return jobs

class LeverNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.board_identity.board_token if hasattr(raw_job.board_identity, 'board_token') else "unknown"
        
        job_list = raw_job.payload.get("jobs", []) if "jobs" in raw_job.payload else [raw_job.payload]
        for job in job_list:
            external_id = str(job.get("id", ""))
            title = job.get("text", "")
            categories = job.get("categories", {})
            location = categories.get("location", "")
            dept_name = categories.get("team", "")
            emp_type = categories.get("commitment", "")
            workplace = job.get("workplaceType", "")
            
            identity = JobIdentity(
                provider="lever",
                board_id=company_id,
                external_job_id=external_id
            )
            
            jobs.append(CanonicalJob(
                identity=identity,
                company_id=company_id,
                board_id=company_id,
                title=title,
                description=job.get("descriptionPlain", ""),
                location=location,
                remote_type=workplace,
                department=dept_name,
                employment_type=emp_type,
                seniority="",
                salary_min=None,
                salary_max=None,
                salary_currency="",
                posted_at=str(job.get("createdAt", "")),
                apply_url=job.get("applyUrl", ""),
                raw_payload=job,
                normalized_at=time.time()
            ))
        return jobs

class AshbyNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.board_identity.board_token if hasattr(raw_job.board_identity, 'board_token') else "unknown"
        
        for job in raw_job.payload.get("jobs", []):
            external_id = str(job.get("id", ""))
            title = job.get("title", "")
            location = job.get("location", "")
            dept_name = job.get("department", "")
            emp_type = job.get("employmentType", "")
            
            identity = JobIdentity(
                provider="ashby",
                board_id=company_id,
                external_job_id=external_id
            )
            
            jobs.append(CanonicalJob(
                identity=identity,
                company_id=company_id,
                board_id=company_id,
                title=title,
                description="",
                location=location,
                remote_type="",
                department=dept_name,
                employment_type=emp_type,
                seniority="",
                salary_min=None,
                salary_max=None,
                salary_currency="",
                posted_at=job.get("publishedAt", ""),
                apply_url=job.get("jobUrl", ""),
                raw_payload=job,
                normalized_at=time.time()
            ))
        return jobs

class SmartRecruitersNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.board_identity.board_token if hasattr(raw_job.board_identity, 'board_token') else "unknown"
        
        for job in raw_job.payload.get("jobPostings", []):
            external_id = str(job.get("id", ""))
            title = job.get("name", "")
            loc_obj = job.get("location", {})
            location = f"{loc_obj.get('city', '')}, {loc_obj.get('region', '')}, {loc_obj.get('country', '')}".strip(', ')
            remote = "Remote" if job.get("remote") else ""
            dept_name = job.get("department", {}).get("label", "")
            emp_type = job.get("typeOfEmployment", {}).get("label", "")
            
            identity = JobIdentity(
                provider="smartrecruiters",
                board_id=company_id,
                external_job_id=external_id
            )
            
            jobs.append(CanonicalJob(
                identity=identity,
                company_id=company_id,
                board_id=company_id,
                title=title,
                description="",
                location=location,
                remote_type=remote,
                department=dept_name,
                employment_type=emp_type,
                seniority="",
                salary_min=None,
                salary_max=None,
                salary_currency="",
                posted_at=job.get("releasedDate", ""),
                apply_url=f"https://jobs.smartrecruiters.com/{company_id}/{external_id}",
                raw_payload=job,
                normalized_at=time.time()
            ))
        return jobs

class WorkdayNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        if not hasattr(raw_job.board_identity, 'tenant'):
            return []
            
        tenant = raw_job.board_identity.tenant
        site = raw_job.board_identity.site
        board_id = f"{tenant}_{site}"
        
        job_list = raw_job.payload.get("jobPostings", []) if "jobPostings" in raw_job.payload else [raw_job.payload]
        for job in job_list:
            # Workday uses a complex alphanumeric externalPath as the URL ID
            external_path = job.get("externalPath", "")
            external_id = external_path.split("/")[-1] if external_path else ""
            if not external_id:
                # Fallback to requisition ID if path is missing
                external_id = job.get("bulletFields", [None])[0]
                
            title = job.get("title", "")
            location = job.get("locationsText", "")
            emp_type = job.get("timeType", "")
            posted = job.get("postedOn", "")
            
            identity = JobIdentity(
                provider="workday",
                board_id=board_id,
                external_job_id=external_id if external_id else None,
                fingerprint=self._generate_fingerprint(tenant, title, location, emp_type) if not external_id else None
            )
            
            apply_url = f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}{external_path}" if external_path else ""
            
            jobs.append(CanonicalJob(
                identity=identity,
                company_id=tenant,
                board_id=board_id,
                title=title,
                description="",
                location=location,
                remote_type="",
                department="",
                employment_type=emp_type,
                seniority="",
                salary_min=None,
                salary_max=None,
                salary_currency="",
                posted_at=posted,
                apply_url=apply_url,
                raw_payload=job,
                normalized_at=time.time()
            ))
        return jobs

class NormalizerFactory:
    @staticmethod
    def get_normalizer(provider: str) -> JobNormalizer:
        normalizers = {
            "greenhouse": GreenhouseNormalizer(),
            "lever": LeverNormalizer(),
            "ashby": AshbyNormalizer(),
            "smartrecruiters": SmartRecruitersNormalizer(),
            "workday": WorkdayNormalizer()
        }
        return normalizers.get(provider)
