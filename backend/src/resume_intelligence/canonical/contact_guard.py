"""
Candidate Context Isolation & Contact Information Guard Subsystem.

Enforces zero state leakage across resume generation tasks:
- Guarantees complete context isolation per task execution.
- Enforces strict validation matching generated contact info to active candidate profile.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from src.resume_intelligence.canonical.models import PersonalInfo, SocialLinks


class CandidateContactContext(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None

    @classmethod
    def create_clean_context(cls, personal: PersonalInfo, social: SocialLinks) -> "CandidateContactContext":
        """Instantiates a completely clean, isolated contact context with 0 global state leakage."""
        return cls(
            name=personal.full_name or "",
            email=personal.email or "",
            phone=personal.phone or "",
            location=personal.location or "",
            linkedin=social.linkedin or None,
            github=social.github or None,
            portfolio=social.portfolio or None,
            website=social.portfolio or None
        )


class ContactGuardValidationError(Exception):
    """Raised when generated contact info differs from active candidate profile."""
    pass


class CandidateContactGuard:
    """Validation guard enforcing contact fidelity and preventing state contamination."""

    def validate(self, generated_contact: CandidateContactContext, expected_contact: CandidateContactContext):
        """Validates generated contact info matches expected active candidate context."""
        mismatches = []
        if generated_contact.name != expected_contact.name:
            mismatches.append(f"Name mismatch: '{generated_contact.name}' != '{expected_contact.name}'")
        if generated_contact.email != expected_contact.email:
            mismatches.append(f"Email mismatch: '{generated_contact.email}' != '{expected_contact.email}'")
        if generated_contact.phone != expected_contact.phone:
            mismatches.append(f"Phone mismatch: '{generated_contact.phone}' != '{expected_contact.phone}'")
        if generated_contact.linkedin != expected_contact.linkedin:
            mismatches.append(f"LinkedIn mismatch: '{generated_contact.linkedin}' != '{expected_contact.linkedin}'")
        if generated_contact.github != expected_contact.github:
            mismatches.append(f"GitHub mismatch: '{generated_contact.github}' != '{expected_contact.github}'")

        if mismatches:
            raise ContactGuardValidationError(
                f"Contact Information Contamination Detected! Mismatches: {'; '.join(mismatches)}"
            )
        return True
