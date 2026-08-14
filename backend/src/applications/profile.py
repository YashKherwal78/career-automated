import os
import json
import logging
from typing import Optional
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ProfileManager")

# Field-name vocabulary this class exposes (first_name, phone, university,
# ...) is form-automation-specific, distinct from user_career_profiles'
# own JSON shape (personal_info.full_name, education[0].institution, ...).
# This maps the latter into the former once per profile load.
def _map_user_profile_to_fields(profile_data: dict) -> dict:
    fields: dict = {}

    personal = profile_data.get("personal_info") or {}
    full_name = (personal.get("full_name") or "").strip()
    if full_name:
        parts = full_name.split(None, 1)
        fields["first_name"] = parts[0]
        fields["last_name"] = parts[1] if len(parts) > 1 else ""
    if personal.get("email"):
        fields["email"] = personal["email"]
    if personal.get("phone"):
        # Profile stores "+91 9891148156" (E.164-ish); base_profile's
        # convention is the bare local number (see the field's original
        # comment -- Greenhouse pairs it with a separate country selector).
        # Strip a leading "+<digits> " country-code prefix if present.
        phone = personal["phone"].strip()
        import re as _re
        stripped = _re.sub(r"^\+\d{1,3}\s+", "", phone)
        fields["phone"] = stripped
        code_match = _re.match(r"^(\+\d{1,3})\s+", phone)
        if code_match:
            fields["phone_country_code"] = code_match.group(1)
    if personal.get("linkedin"):
        fields["linkedin"] = personal["linkedin"]
    if personal.get("github"):
        fields["github"] = personal["github"]
    if personal.get("portfolio"):
        fields["portfolio"] = personal["portfolio"]
        fields["website"] = personal["portfolio"]
    if personal.get("location"):
        fields["location"] = personal["location"]
        fields["current_location"] = personal["location"]
        fields["residence_location"] = personal["location"]

    experience = profile_data.get("experience") or []
    if experience:
        fields["years_experience"] = len(experience)
        fields["total_experience_years"] = len(experience)
        latest = experience[0]
        company = latest.get("company")
        if company:
            fields["current_employer"] = company
            fields["current_organization"] = company

    education = profile_data.get("education") or []
    if education:
        top = education[0]
        degree = top.get("degree")
        institution = top.get("institution")
        field_of_study = top.get("field_of_study")
        end_date = top.get("end_date")
        if degree:
            fields["degree"] = degree
            fields["highest_degree"] = degree
        if institution:
            fields["university"] = institution
            fields["college"] = institution
            fields["education_university"] = institution
            fields["institution"] = institution
        if field_of_study:
            fields["branch"] = field_of_study
        if end_date:
            fields["graduation_year"] = end_date
            fields["education_end"] = end_date
            fields["graduation_date"] = end_date

    prefs = profile_data.get("career_preferences") or {}
    if prefs.get("locations"):
        fields["preferred_locations"] = prefs["locations"]
    if prefs.get("min_salary"):
        fields["expected_salary"] = prefs["min_salary"]
        fields["expected_full_time_ctc"] = prefs["min_salary"]
    if "open_to_relocation" in prefs and prefs["open_to_relocation"] is not None:
        fields["relocation"] = prefs["open_to_relocation"]
        fields["open_to_relocation"] = prefs["open_to_relocation"]
        fields["available_to_relocate"] = prefs["open_to_relocation"]

    return fields


# Fields where silently falling back to base_profile's hardcoded identity
# would misattribute the application to the wrong person -- these must
# come from the real per-user profile or be left blank, never defaulted.
_IDENTITY_FIELDS = {"first_name", "last_name", "email", "phone"}

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
    def __init__(self, profile_type: str = "AI_PROFILE", user_id: Optional[str] = None):
        self.profile_type = profile_type
        self.user_id = user_id

        # base_profile below was, until this fix, the *only* source of
        # identity/personal-info fields for every user's auto-apply run --
        # meaning every application, for every user, filled forms with the
        # product owner's own name/email/phone/education. It now only
        # serves as: (a) the legacy no-user_id fallback for any call site
        # not yet passing one, and (b) a best-effort default for fields
        # that have no per-user equivalent in user_career_profiles yet
        # (EEO/demographic answers, non-India work authorization, expected
        # compensation, notice period) -- identity fields are handled
        # separately below and never fall back to this dict once a
        # user_id is given (see _IDENTITY_FIELDS / get_field).
        self.user_profile: dict = self._load_user_profile(user_id) if user_id else {}

        # Base fallback profile
        self.base_profile = {
            # Personal Information
            "first_name": "Yash",
            "last_name": "Kherwal",
            "email": "yash.kherwal78@gmail.com",
            # No "+91 " prefix: Greenhouse's phone field pairs with a separate
            # country-code selector (already defaults to India) — the input
            # itself should just be the local number, not the full E.164 form.
            "phone": "9891148156",
            "linkedin": "https://www.linkedin.com/in/yash-kherwal-944497254/",
            "github": "https://github.com/YashKherwal78",
            # Listed on the current resume header alongside LinkedIn/GitHub —
            # previously missing here entirely, so any "portfolio/website"
            # question silently fell back to the GitHub URL instead.
            "portfolio": "https://careerautomated.in",
            "website": "https://careerautomated.in",
            "location": "Ghaziabad, India",
            # Location
            "address": "Niti Khand 3, Indirapuram",
            "postal_code": "201014",
            "zip_code": "201014",
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
            "transgender_status": "No",
            # Standard Greenhouse EEO template wording — this survey is
            # voluntary and explicitly doesn't affect the hiring decision,
            # so decline rather than guess an inaccurate category.
            "race": "Decline to Self Identify",
            "has_criminal_record": False,
            
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
        
        # master_candidate_profile.json is the product owner's own
        # "self-learning" export -- loading it for a real per-user run
        # would leak the same identity-misattribution bug this fix exists
        # to close, just through a second static-file source instead of
        # base_profile. Only the legacy (no user_id) path uses it now.
        self.dynamic_profile = self._load_master_json() if not user_id else {}

    def _load_master_json(self) -> dict:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "context", "master_candidate_profile.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_user_profile(self, user_id: str) -> dict:
        try:
            from src.api.db import get_connection
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT profile_data FROM public.user_career_profiles WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
                row = cursor.fetchone()
            if not row:
                return {}
            profile_data = row["profile_data"] if hasattr(row, "keys") else row[0]
            if not profile_data:
                return {}
            profile = json.loads(profile_data) if isinstance(profile_data, str) else profile_data
            return _map_user_profile_to_fields(profile)
        except Exception as e:
            logger.warning(f"ProfileManager: per-user profile load failed for user_id={user_id}: {e}")
            return {}

    def get_field(self, field_name: str):
        """Returns the fact value.

        With a user_id: real per-user data wins; identity fields
        (name/email/phone) never fall back to base_profile's hardcoded
        values if the real profile doesn't have them -- better to return
        an empty string (surfacing as a validation gap / REVIEW_REQUIRED
        upstream) than to silently submit someone else's application under
        the wrong person's name. Non-identity fields (EEO answers, work
        auth, compensation, ...) still fall back to base_profile as a
        best-effort default, since no per-user data model for those exists
        yet -- same behavior as before this fix, just no longer covering
        identity too.

        Without a user_id (legacy call sites): unchanged -- dynamic JSON
        first, then base_profile.
        """
        if self.user_id:
            if field_name in self.user_profile:
                return self.user_profile[field_name]
            if field_name in _IDENTITY_FIELDS:
                return ""
            return self.base_profile.get(field_name, "")

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
        if self.user_id:
            merged = dict(self.base_profile)
            for field in _IDENTITY_FIELDS:
                merged[field] = ""  # never leak owner identity into another user's run
            merged.update(self.user_profile)
            return merged
        return self.base_profile
        
    def get_llm_context(self) -> str:
        if self.profile_type == "AI_PROFILE":
            return self.ai_context
        elif self.profile_type == "BUSINESS_PROFILE":
            return self.business_context
        elif self.profile_type == "SDE_PROFILE":
            return self.sde_context
        return self.ai_context
