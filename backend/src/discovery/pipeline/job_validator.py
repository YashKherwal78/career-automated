from typing import List, Optional
from src.discovery.models import CanonicalJob

class JobValidator:
    """Validates jobs before persistence to prevent corrupt data."""
    
    @classmethod
    def validate(cls, job: CanonicalJob) -> List[str]:
        """Returns a list of error messages. Empty list means valid."""
        errors = []
        
        if not job.title or not str(job.title).strip():
            errors.append("Missing required field: title")
            
        if not job.apply_url or not str(job.apply_url).strip():
            errors.append("Missing required field: apply_url")
            
        if not job.identity:
            errors.append("Missing JobIdentity")
        else:
            try:
                # Ensure hash can be generated
                job.identity.get_hash()
            except Exception as e:
                errors.append(f"Invalid JobIdentity: {str(e)}")
                
        return errors
        
    @classmethod
    def filter_valid(cls, jobs: List[CanonicalJob]) -> tuple[List[CanonicalJob], List[dict]]:
        """Returns (valid_jobs, invalid_records)."""
        valid = []
        invalid = []
        for j in jobs:
            errors = cls.validate(j)
            if not errors:
                valid.append(j)
            else:
                invalid.append({"job": j, "errors": errors})
        return valid, invalid
