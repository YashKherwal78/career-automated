"""
Converts the stored candidate profile_data (as saved by PUT /candidate/profile,
see candidate.py's ProfileDataPayload) into an ExtendedStructuredResume — the
pure-presentation model the Jake's Resume renderer consumes.

Deterministic mapping only. No LLM calls.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.resume_intelligence.compiler.jake_resume.extended_models import (
    ExtendedStructuredResume,
    CustomSection,
    CustomSectionItem,
)
from src.resume_intelligence.compiler.jake_resume.models import (
    StructuredContact,
    StructuredEducation,
    StructuredExperience,
    StructuredProject,
    StructuredSkillCategory,
)

DEFAULT_SECTION_ORDER = ["summary", "education", "experience", "projects", "skills"]


def _split_bullets(description: str) -> List[str]:
    if not description:
        return []
    return [line.strip("-• \t") for line in description.split("\n") if line.strip()]


def _entry_bullets(entry: Dict[str, Any]) -> List[str]:
    """
    Experience entries from ProfileExtractionService carry bullets as a list
    under "bullet_points", not a "description" string — prefer that shape and
    fall back to splitting "description" for any other producer of profile_data.
    """
    bullet_points = entry.get("bullet_points")
    if bullet_points:
        return [b.strip() for b in bullet_points if isinstance(b, str) and b.strip()]
    return _split_bullets(entry.get("description") or "")


def build_structured_resume(profile_data: Dict[str, Any]) -> ExtendedStructuredResume:
    personal_info = profile_data.get("personal_info") or {}
    contact = StructuredContact(
        phone=personal_info.get("phone") or "",
        email=personal_info.get("email") or "",
        linkedin=personal_info.get("linkedin") or "",
        github=personal_info.get("github") or "",
        location=personal_info.get("location") or "",
        portfolio=personal_info.get("portfolio") or None,
    )

    education = [
        StructuredEducation(
            institution=e.get("institution") or "",
            degree=e.get("degree") or "",
            field_of_study=e.get("field_of_study") or "",
            start_date=e.get("start_date") or "",
            end_date=e.get("end_date") or "",
            location=e.get("location") or "",
            gpa=e.get("gpa") or None,
        )
        for e in (profile_data.get("education") or [])
        if e.get("institution")
    ]

    experience = [
        StructuredExperience(
            company=e.get("company") or "",
            title=e.get("role") or e.get("title") or "",
            location=e.get("location") or "",
            start_date=e.get("start_date") or "",
            end_date=e.get("end_date") or "",
            bullets=_entry_bullets(e),
            technologies=e.get("technologies") or [],
        )
        for e in (profile_data.get("experience") or [])
        if e.get("company")
    ]

    projects = [
        StructuredProject(
            title=p.get("name") or p.get("title") or "",
            technologies=(
                [t.strip() for t in p["technologies"].split(",") if t.strip()]
                if isinstance(p.get("technologies"), str)
                else (p.get("technologies") or [])
            ),
            date=p.get("date") or "",
            bullets=_entry_bullets(p),
            url=p.get("url") or None,
        )
        for p in (profile_data.get("projects") or [])
        if p.get("name") or p.get("title")
    ]

    skills_raw = profile_data.get("skills") or {}
    skill_categories = [
        StructuredSkillCategory(category_name=_humanize_category(category), skills=skills)
        for category, skills in skills_raw.items()
        if skills
    ]

    custom_sections = [
        CustomSection(
            section_title=sec.get("section_title") or sec.get("title") or "Additional",
            items=[
                CustomSectionItem(
                    title=item.get("title") or "",
                    subtitle=item.get("subtitle") or None,
                    date=item.get("date") or None,
                    location=item.get("location") or None,
                    bullets=_split_bullets(item.get("description") or "")
                    or (item.get("bullets") or []),
                    technologies=item.get("technologies") or [],
                )
                for item in (sec.get("items") or [])
            ],
        )
        for sec in (profile_data.get("custom_sections") or [])
        if (sec.get("section_title") or sec.get("title"))
    ]

    section_order = list(DEFAULT_SECTION_ORDER)
    for sec in custom_sections:
        section_order.append(f"custom:{sec.section_title}")

    return ExtendedStructuredResume(
        name=personal_info.get("full_name") or "",
        contact=contact,
        summary=profile_data.get("summary") or None,
        education=education,
        experience=experience,
        projects=projects,
        skill_categories=skill_categories,
        custom_sections=custom_sections,
        section_order=section_order,
    )


def _humanize_category(category: str) -> str:
    """Legacy snake_case category keys ("developer_tools") get title-cased
    for display. Newer extractions already store display-ready category
    names directly ("AI & Agents", "Languages & Backend") -- title-casing
    those would mangle "AI" into "Ai", so a key that already contains a
    space is passed through unchanged rather than re-cased."""
    if " " in category:
        return category
    return category.replace("_", " ").title()
