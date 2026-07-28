"""
Adapter translating CanonicalCandidateProfile into StructuredResume for Jake Compiler V1.
"""

from src.resume_intelligence.canonical.models import CanonicalCandidateProfile
from src.resume_intelligence.compiler.jake_resume.models import (
    StructuredResume, StructuredContact, StructuredEducation,
    StructuredExperience, StructuredProject, StructuredSkillCategory
)


def canonical_to_structured(profile: CanonicalCandidateProfile, section_order: list = None) -> StructuredResume:
    """Translates CanonicalCandidateProfile into compiler-consumable StructuredResume."""
    contact = StructuredContact(
        phone=profile.personal.phone,
        email=profile.personal.email,
        linkedin=profile.social_links.linkedin or "",
        github=profile.social_links.github or "",
        location=profile.personal.location,
        portfolio=profile.social_links.portfolio
    )

    education = [
        StructuredEducation(
            institution=edu.institution,
            degree=edu.degree,
            field_of_study=edu.field_of_study,
            start_date=edu.start_date,
            end_date=edu.end_date,
            location=edu.location,
            gpa=edu.gpa
        )
        for edu in profile.education
    ]

    experience = [
        StructuredExperience(
            company=exp.company,
            title=exp.title,
            location=exp.location,
            start_date=exp.start_date,
            end_date=exp.end_date,
            bullets=exp.bullets,
            technologies=exp.technologies
        )
        for exp in profile.experience
    ]

    projects = [
        StructuredProject(
            title=proj.title,
            technologies=proj.technologies,
            date=proj.date,
            bullets=proj.bullets,
            url=proj.live_link or proj.github_link
        )
        for proj in profile.projects
    ]

    skill_categories = []
    if profile.skills.ai_ml:
        skill_categories.append(StructuredSkillCategory(category_name="AI/ML", skills=profile.skills.ai_ml))
    if profile.skills.product_management:
        skill_categories.append(StructuredSkillCategory(category_name="Product", skills=profile.skills.product_management))
    if profile.skills.devops_infra:
        skill_categories.append(StructuredSkillCategory(category_name="Backend & Infra", skills=profile.skills.devops_infra))
    if profile.skills.data_analytics:
        skill_categories.append(StructuredSkillCategory(category_name="Data & Analytics", skills=profile.skills.data_analytics))

    order = section_order or ["education", "experience", "projects", "skills"]

    return StructuredResume(
        name=profile.personal.full_name,
        contact=contact,
        summary=profile.personal.summary,
        education=education,
        experience=experience,
        projects=projects,
        skill_categories=skill_categories,
        section_order=order
    )
