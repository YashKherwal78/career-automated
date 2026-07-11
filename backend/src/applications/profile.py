import os
import json
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

class CryptoManager:
    def __init__(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY not found in environment.")
        self.cipher = Fernet(key.encode())
        
    def encrypt(self, password: str) -> str:
        return self.cipher.encrypt(password.encode()).decode()
        
    def decrypt(self, encrypted_password: str) -> str:
        return self.cipher.decrypt(encrypted_password.encode()).decode()

class ProfileManager:
    """Manages the candidate profile used for form automation. Self-Learning V2."""
    def __init__(self, profile_type: str = "AI_PROFILE"):
        self.profile_type = profile_type
        
        # Base fallback profile
        self.base_profile = {
            # Personal Information
            "first_name": "Yash",
            "last_name": "Kherwal",
            "email": "yash.kherwal78@gmail.com",
            "phone": "+91 9891148156",
            "linkedin": "https://www.linkedin.com/in/yash-kherwal-944497254/",
            "location": "Roorkee, India",
            # Location
            "address": "Niti Khand 3, Indirapuram",
            "city": "Ghaziabad",
            "district": "Ghaziabad",
            "state": "Uttar Pradesh",
            "country": "India",
            "current_location": "Ghaziabad, Uttar Pradesh, India",
            "residence_location": "Ghaziabad, Uttar Pradesh, India",
            "phone_country_code": "+91",
            
            # Education Update
            "university": "IIT Roorkee",
            "degree": "B.Tech",
            "branch": "Chemical Engineering",
            "graduation_year": "2026",
            
            # Employment Update
            "notice_period": "15 days",
            "years_experience": 0,
            
            # Preferences Update
            "relocation": "Yes",
            "travel": "Yes",
            "max_travel_percentage": "50",
            
            # Work Auth Update
            "authorized_to_work_india": "Yes",
            "requires_india_sponsorship": "No",

            
            # Education
            "degree": "B.Tech",
            "highest_degree": "B.Tech",
            "institution": "IIT Roorkee",
            "college": "IIT Roorkee",
            "education_university": "Indian Institute of Technology Roorkee",
            "graduation_year": "2026",
            "education_status": "Graduated",
            "currently_enrolled": False,
            "education_start": "2022",
            "education_end": "2026",
            
            # Employment
            "employment_status": "Recent Graduate",
            "current_employer": "Not Currently Employed",
            "current_organization": "IIT Roorkee",
            "years_experience": 0,
            "total_experience_years": 0,
            "notice_period_days": 15,
            
            # Legal / Compliance
            "gender": "Male",
            "bgv_consent": True,
            "has_relatives_at_company": False,
            "has_relative_in_company": False,
            "previous_employee": False,
            "previously_employed": False,
            "military_status": False,
            "security_clearance": False,
            
            # Mobility
            "open_to_relocation": True,
            "available_to_relocate": True,
            "open_to_travel": True,
            "available_to_travel": True,
            
            # Work Authorization
            "work_authorized_india": True,
            "work_authorization": True,
            "work_authorized_us": False,
            "work_authorized_uk": False,
            "work_authorized_eu": False,
            "requires_sponsorship_us": True,
            "requires_sponsorship_uk": True,
            "requires_sponsorship_eu": True,
            "visa_sponsorship_required": False,    
            # Demographics
            "gender": "Male",
            "veteran_status": "No",
            "disability_status": "No",
            "hispanic_latino": "No",
            
            # V2.1 COMPENSATION
            "expected_full_time_ctc": "15,00,000 INR",
            "expected_internship_stipend": "50,000 INR",
            "expected_salary": "15,00,000 INR",
            "salary_negotiable": True,
            "preferred_currency": "INR",
            
            # V2.1 AVAILABILITY
            "graduation_date": "May 2026",
            "earliest_start_date": "2026-07-01",
            "latest_start_date": "2026-08-01",
            "available_for_internship": True,
            "available_for_full_time": True,
            "notice_period": "0 Days",
            
            # V2.1 LANGUAGES
            "english_proficiency": "Professional",
            "hindi_proficiency": "Native",
            "other_languages": "None",
            
            # V2.1 WORK PREFERENCES
            "relocation": True,
            "travel": True,
            "remote": True,
            "hybrid": True,
            "onsite": True
        }
        
        # Profile specific contexts for LLM
        self.ai_context = "I am an AI/ML Engineer with expertise in GenAI, LangChain, RAG, and Python. Built autonomous agents."
        self.sde_context = "I am a Software Development Engineer skilled in Python, React, NextJS, and full-stack development."
        self.business_context = "I am a Product Manager / Business Analyst skilled in Go-To-Market strategies, Product Roadmapping, and data-driven insights."
        
        self.dynamic_profile = self._load_master_json()

    def _load_master_json(self) -> dict:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "context", "master_candidate_profile.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
        
    def get_field(self, field_name: str):
        """Returns the fact value. Uses dynamic JSON if confidence >= 70 or human_verified == True."""
        # 1. Check dynamic JSON first
        if field_name in self.dynamic_profile:
            field_data = self.dynamic_profile[field_name]
            if isinstance(field_data, dict):
                is_human = field_data.get("human_verified", False)
                conf = field_data.get("confidence", 0)
                val = field_data.get("value")
                
                # Trust human verified over anything else
                if is_human and val is not None:
                    return val
                
                # Trust extracted if confidence is sufficient
                if conf >= 70 and val is not None:
                    return val

        # 2. Fallback to base
        return self.base_profile.get(field_name, "")
        
    def get_full_profile(self) -> dict:
        return self.base_profile
        
    def get_llm_context(self) -> str:
        if self.profile_type == "AI_PROFILE":
            return self.ai_context
        elif self.profile_type == "BUSINESS_PROFILE":
            return self.business_context
        elif self.profile_type == "SDE_PROFILE":
            return self.sde_context
        return self.ai_context
