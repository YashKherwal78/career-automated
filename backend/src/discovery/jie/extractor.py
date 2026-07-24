import hashlib
import datetime
from typing import Dict, Any

from src.discovery.jie.models import StructuredJob
from src.discovery.jie.extractors.preprocessing import preprocess_jd
from src.discovery.jie.extractors.basic import extract_basic_info
from src.discovery.jie.extractors.location import extract_location
from src.discovery.jie.extractors.employment_type import extract_employment_type
from src.discovery.jie.extractors.experience import extract_experience
from src.discovery.jie.extractors.salary import extract_salary
from src.discovery.jie.extractors.education import extract_education
from src.discovery.jie.extractors.technologies import extract_technologies
from src.discovery.jie.extractors.skills import extract_skills
from src.discovery.jie.extractors.responsibilities import extract_responsibilities
from src.discovery.jie.extractors.requirements import extract_requirements, generate_legacy_requirements
from src.discovery.jie.extractors.benefits import extract_benefits
from src.discovery.jie.extractors.dates import extract_dates

JIE_VERSION = "2.0.0"

class JDExtractor:
    def __init__(self):
        pass

    def _hash_jd(self, jd_text: str) -> str:
        return hashlib.md5(jd_text.encode('utf-8')).hexdigest()

    def extract(self, title: str, jd_text: str, metadata: Dict[str, Any] = None) -> StructuredJob:
        """Orchestrates modular sub-extractors to parse a job description without calling LLMs."""
        if metadata is None:
            metadata = {}
            
        jd_hash = self._hash_jd(jd_text)
        # Use timezone-aware UTC datetime format
        parsed_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        
        # 1. Preprocess
        clean_text = preprocess_jd(jd_text)
        
        # 2. Extract Stage Modules
        basic = extract_basic_info(title, clean_text, metadata)
        loc = extract_location(clean_text, title, metadata)
        emp_type = extract_employment_type(title, clean_text)
        exp = extract_experience(clean_text)
        sal = extract_salary(clean_text)
        edu = extract_education(clean_text)
        techs = extract_technologies(clean_text)
        skills = extract_skills(clean_text)
        resp = extract_responsibilities(clean_text)
        reqs = extract_requirements(clean_text)
        benefits = extract_benefits(clean_text)
        dates = extract_dates(clean_text)
        
        # 3. Generate Legacy Requirements for backward compatibility checks
        legacy_reqs = generate_legacy_requirements(reqs, techs, skills)
        
        return StructuredJob(
            jd_hash=jd_hash,
            jie_version=JIE_VERSION,
            parsed_at=parsed_at,
            title=basic["title"],
            company=basic["company"],
            job_url=basic["job_url"],
            job_id=basic["job_id"],
            location=loc["location"],
            work_mode=loc["work_mode"],
            employment_type=emp_type,
            experience_min=exp["experience_min"],
            experience_max=exp["experience_max"],
            fresher_friendly=exp["fresher_friendly"],
            salary=sal,
            education=edu,
            technologies=techs,
            skills=skills,
            responsibilities=resp,
            requirements=legacy_reqs, # Keeping model property populated with legacy Requirements
            benefits=benefits,
            posted_date=dates["posted_date"],
            application_deadline=dates["application_deadline"],
            domain=metadata.get("domain", "Unknown"),
            parser_metadata={
                "ats_provider": basic["ats_provider"],
                "raw_requirements": reqs
            }
        )
