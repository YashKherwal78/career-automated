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
        company_id = raw_job.company_id
        
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
        company_id = raw_job.company_id
        
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
        company_id = raw_job.company_id
        
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
                description=job.get("descriptionPlain") or job.get("descriptionHtml") or "",
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
        company_id = raw_job.company_id
        postings = []
        if isinstance(raw_job.payload, dict):
            if "jobPostings" in raw_job.payload:
                postings = raw_job.payload.get("jobPostings", [])
            elif "id" in raw_job.payload:
                postings = [raw_job.payload]
                
        for job in postings:
            external_id = str(job.get("id", ""))
            title = job.get("name", "")
            loc_obj = job.get("location", {})
            location = f"{loc_obj.get('city', '')}, {loc_obj.get('region', '')}, {loc_obj.get('country', '')}".strip(', ')
            remote = "Remote" if (job.get("remote") or loc_obj.get("remote")) else ""
            dept_name = job.get("department", {}).get("label", "")
            emp_type = job.get("typeOfEmployment", {}).get("label", "")
            
            identity = JobIdentity(
                provider="smartrecruiters",
                board_id=company_id,
                external_job_id=external_id
            )
            
            board_token = getattr(raw_job.board_identity, "board_token", company_id) or company_id
            
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
                apply_url=f"https://jobs.smartrecruiters.com/{board_token}/{external_id}",
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

class TeamtailorNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload
        
        # Raw payload key mapping for JSONFeed/Microdata schema
        title = job.get("title") or job.get("name") or ""
        external_id = str(job.get("id") or "")
        description = job.get("descriptionPlain") or job.get("descriptionHtml") or job.get("description") or ""
        
        # Determine location
        location = ""
        loc_obj = job.get("jobLocation") or job.get("location")
        if isinstance(loc_obj, dict):
            address = loc_obj.get("address")
            if isinstance(address, dict):
                location = address.get("addressLocality") or address.get("addressCountry") or ""
            else:
                location = loc_obj.get("name") or ""
        elif isinstance(loc_obj, str):
            location = loc_obj

        apply_url = job.get("url") or job.get("applyUrl") or ""
        
        identity = JobIdentity(
            provider="teamtailor",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )
        
        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=description,
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("date_published") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class WorkableNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload
        
        title = job.get("title") or ""
        external_id = str(job.get("id") or job.get("shortcode") or "")
        
        location = ""
        loc_obj = job.get("location")
        if isinstance(loc_obj, dict):
            location = loc_obj.get("city") or loc_obj.get("country") or ""
        elif isinstance(loc_obj, str):
            location = loc_obj
            
        remote = "Remote" if job.get("workplace") == "remote" or job.get("remote") else ""
        
        identity = JobIdentity(
            provider="workable",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )
        
        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("descriptionPlain") or job.get("description") or "",
            location=location,
            remote_type=remote,
            department=job.get("department") or "",
            employment_type=job.get("employment_type") or "",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class BambooHRNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload
        
        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        
        identity = JobIdentity(
            provider="bamboohr",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )
        
        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=job.get("department") or "",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class OracleNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload
        
        title = job.get("Title") or job.get("title") or ""
        external_id = str(job.get("RequisitionNumber") or job.get("Id") or "")
        location = job.get("PrimaryLocation") or job.get("Location") or ""
        
        identity = JobIdentity(
            provider="oracle",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )
        
        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("Description") or "",
            location=location,
            remote_type="",
            department=job.get("Organization") or "",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("PostedDate") or "",
            apply_url=job.get("ApplyUrl") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class JoinComNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload
        
        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        
        # Build apply URL using the job's idParam slug
        slug = job.get("idParam") or ""
        apply_url = f"https://join.com/companies/{company_id}/{slug}" if slug else ""
        
        # Resolve location details
        location = ""
        city_obj = job.get("city")
        if isinstance(city_obj, dict):
            city_name = city_obj.get("cityName") or ""
            country_name = city_obj.get("countryName") or ""
            location = f"{city_name}, {country_name}".strip(", ")
            
        # Workplace remote translation
        remote = ""
        workplace = job.get("workplaceType")
        if workplace in ("REMOTE", "HYBRID"):
            remote = "Remote" if workplace == "REMOTE" else "Hybrid"
            
        # Salary details
        salary_min = None
        salary_currency = ""
        salary_obj = job.get("salaryAmountFrom")
        if isinstance(salary_obj, dict):
            raw_amount = salary_obj.get("amount")
            if raw_amount is not None:
                # amount in join.com payload is stored in cents/multiplied by 100
                salary_min = float(raw_amount) / 100.0
            salary_currency = salary_obj.get("currency") or ""
            
        emp_type = ""
        emp_obj = job.get("employmentType")
        if isinstance(emp_obj, dict):
            emp_type = emp_obj.get("name") or ""
            
        dept = ""
        cat_obj = job.get("category")
        if isinstance(cat_obj, dict):
            dept = cat_obj.get("name") or ""

        identity = JobIdentity(
            provider="join_com",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )
        
        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",  # Listing page doesn't contain description (separately fetched during enrichment)
            location=location,
            remote_type=remote,
            department=dept,
            employment_type=emp_type,
            seniority="",
            salary_min=salary_min,
            salary_max=None,
            salary_currency=salary_currency,
            posted_at=job.get("createdAt") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class JazzHRNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        apply_url = job.get("url") or ""

        remote = ""
        if location and "remote" in location.lower():
            remote = "Remote"

        identity = JobIdentity(
            provider="jazzhr",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department=department,
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class PersonioNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="personio",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class RecruiteeNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="recruitee",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_currency=job.get("salary_currency") or "",
            posted_at=job.get("created_at") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class BreezyNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="breezy",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class PinpointNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="pinpoint",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_currency=job.get("salary_currency") or "",
            posted_at=job.get("created_at") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class RecruiterboxNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="recruiterbox",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class RemoteOKNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""

        identity = JobIdentity(
            provider="remoteok",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="Remote",
            department="",
            employment_type="",
            seniority="",
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_currency="USD",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class WellfoundNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""

        identity = JobIdentity(
            provider="wellfound",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class WeWorkRemotelyNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""

        identity = JobIdentity(
            provider="weworkremotely",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="Remote",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class TheHubNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""
        department = job.get("department") or ""

        identity = JobIdentity(
            provider="thehub",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=department,
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class MercorNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""

        identity = JobIdentity(
            provider="mercor",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class ManfredNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""
        remote = job.get("remote") or ""

        identity = JobIdentity(
            provider="manfred",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department="",
            employment_type="",
            seniority="",
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_currency=job.get("salary_currency") or "",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class WantedNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""

        identity = JobIdentity(
            provider="wanted",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=job.get("url") or "",
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class SuccessFactorsNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="successfactors",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, "", "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location="",
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class GemNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="gem",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class iCIMSNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="icims",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=department,
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class RipplingNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        apply_url = job.get("url") or ""

        # Map Rippling's employmentType label enum
        _type_map = {
            "SALARIED_FT": "FULL_TIME",
            "SALARIED_PT": "PART_TIME",
            "HOURLY_FT": "FULL_TIME",
            "HOURLY_PT": "PART_TIME",
            "CONTRACTOR": "CONTRACT",
            "CONTRACT": "CONTRACT",
            "TEMPORARY": "TEMPORARY",
            "INTERN": "INTERN",
            "INTERNSHIP": "INTERN",
            "FULL_TIME": "FULL_TIME",
            "PART_TIME": "PART_TIME",
        }
        mapped_type = _type_map.get(employment_type, employment_type)

        identity = JobIdentity(
            provider="rippling",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=department,
            employment_type=mapped_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class CornerstoneNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="cornerstone",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class PhenomNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="phenom",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class AvatureNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="avature",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department=department,
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class EightfoldNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        employment_type = job.get("employment_type") or ""
        remote = job.get("remote") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="eightfold",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type=remote,
            department=department,
            employment_type=employment_type,
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class BuiltInNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="builtin",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, "", "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location="",
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class AppleNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        department = job.get("department") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="apple",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type="",
            department=department,
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class ArbetsformedlingenNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or ""
        location = job.get("location") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="arbetsformedlingen",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class BundesagenturNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or ""
        location = job.get("location") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="bundesagentur",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description="",
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at=job.get("created_at") or "",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class EuresNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or ""
        location = job.get("location") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="eures",
            board_id=company_id,
            external_job_id=external_id if external_id else None,
            fingerprint=self._generate_fingerprint(company_id, title, location, "") if not external_id else None
        )

        jobs.append(CanonicalJob(
            identity=identity,
            company_id=company or company_id,
            board_id=company_id,
            title=title,
            description=job.get("description") or "",
            location=location,
            remote_type="",
            department="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
class JobsCzNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""
        apply_url = job.get("url") or ""
        salary_text = job.get("salary") or ""

        # Simple parsing for Czech salary format: "40 000 – 60 000 Kč"
        salary_min = None
        salary_max = None
        salary_currency = ""
        if "Kč" in salary_text:
            salary_currency = "CZK"
            # Extract numbers from format
            nums = [int(s) for s in re.findall(r"\d[\d\s]*", salary_text.replace(" ", "").replace(" ", "")) if s]
            if len(nums) == 2:
                salary_min = float(nums[0])
                salary_max = float(nums[1])
            elif len(nums) == 1:
                salary_min = float(nums[0])

        identity = JobIdentity(
            provider="jobs_cz",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location=location,
            description="",
            employment_type="",
            seniority="",
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class JobsChNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        location = job.get("location") or ""
        company = job.get("company") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="jobsch",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location=location,
            description="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class GoogleNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="google",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company="Google",
            location="Global",
            description="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class TaleoNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or ""
        apply_url = job.get("url") or ""

        identity = JobIdentity(
            provider="taleo",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location="",
            description="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class ProgramathorNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or ""
        apply_url = job.get("url") or ""
        location = job.get("location") or ""
        salary_text = job.get("salary") or ""

        # Simple parsing for Programathor BRL salary format: "R$ 3.000 - R$ 5.000"
        salary_min = None
        salary_max = None
        salary_currency = ""
        if "R$" in salary_text:
            salary_currency = "BRL"
            # Extract numbers from format
            nums = [int(s) for s in re.findall(r"\d[\d\.]*", salary_text.replace(" ", "").replace(".", "")) if s]
            if len(nums) == 2:
                salary_min = float(nums[0])
                salary_max = float(nums[1])
            elif len(nums) == 1:
                salary_min = float(nums[0])

        identity = JobIdentity(
            provider="programathor",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location=location,
            description="",
            employment_type="",
            seniority="",
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class TikTokNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or "TikTok"
        apply_url = job.get("url") or ""
        location = job.get("location") or ""
        department = job.get("department") or ""

        identity = JobIdentity(
            provider="tiktok",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location=location,
            description="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class UberNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or "Uber"
        apply_url = job.get("url") or ""
        location = job.get("location") or ""
        department = job.get("department") or ""

        identity = JobIdentity(
            provider="uber",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location=location,
            description="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
            apply_url=apply_url,
            raw_payload=job,
            normalized_at=time.time()
        ))
        return jobs

class WelcomeToTheJungleNormalizer(JobNormalizer):
    def normalize(self, raw_job: RawJob) -> List[CanonicalJob]:
        jobs = []
        company_id = raw_job.company_id
        job = raw_job.payload

        title = job.get("title") or ""
        external_id = str(job.get("id") or "")
        company = job.get("company") or ""
        apply_url = job.get("url") or ""
        location = job.get("location") or ""

        identity = JobIdentity(
            provider="welcometothejungle",
            company_id=company_id,
            external_id=external_id
        )

        jobs.append(CanonicalJob(
            identity=identity,
            title=title,
            company=company,
            location=location,
            description="",
            employment_type="",
            seniority="",
            salary_min=None,
            salary_max=None,
            salary_currency="",
            posted_at="",
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
            "workday": WorkdayNormalizer(),
            "teamtailor": TeamtailorNormalizer(),
            "workable": WorkableNormalizer(),
            "bamboohr": BambooHRNormalizer(),
            "oracle": OracleNormalizer(),
            "join_com": JoinComNormalizer(),
            "jazzhr": JazzHRNormalizer(),
            "personio": PersonioNormalizer(),
            "recruitee": RecruiteeNormalizer(),
            "breezy": BreezyNormalizer(),
            "pinpoint": PinpointNormalizer(),
            "recruiterbox": RecruiterboxNormalizer(),
            "remoteok": RemoteOKNormalizer(),
            "wellfound": WellfoundNormalizer(),
            "weworkremotely": WeWorkRemotelyNormalizer(),
            "thehub": TheHubNormalizer(),
            "mercor": MercorNormalizer(),
            "manfred": ManfredNormalizer(),
            "wanted": WantedNormalizer(),
            "successfactors": SuccessFactorsNormalizer(),
            "gem": GemNormalizer(),
            "icims": iCIMSNormalizer(),
            "rippling": RipplingNormalizer(),
            "cornerstone": CornerstoneNormalizer(),
            "phenom": PhenomNormalizer(),
            "avature": AvatureNormalizer(),
            "eightfold": EightfoldNormalizer(),
            "builtin": BuiltInNormalizer(),
            "apple": AppleNormalizer(),
            "arbetsformedlingen": ArbetsformedlingenNormalizer(),
            "bundesagentur": BundesagenturNormalizer(),
            "eures": EuresNormalizer(),
            "jobs_cz": JobsCzNormalizer(),
            "jobsch": JobsChNormalizer(),
            "google": GoogleNormalizer(),
            "taleo": TaleoNormalizer(),
            "programathor": ProgramathorNormalizer(),
            "tiktok": TikTokNormalizer(),
            "uber": UberNormalizer(),
            "welcometothejungle": WelcomeToTheJungleNormalizer(),
        }
        return normalizers.get(provider)


