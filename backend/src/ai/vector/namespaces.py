from enum import Enum

class VectorNamespaces(str, Enum):
    RESUME_KB = "resume_kb"
    CAREER_KB = "career_kb"
    USER_MEMORY = "user_memory"
    DOCUMENTS = "documents"
    JOBS = "jobs"
    COMPANIES = "companies"
