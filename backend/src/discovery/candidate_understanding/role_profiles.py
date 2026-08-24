"""
Structured candidate understanding: builds user_career_profiles.structured_profile
(migration 048) from the existing flat profile_data, additively -- nothing
existing reads or depends on this, and profile_data itself is untouched.

Computed once at profile-save time (see api/routers/candidate.py's
update_career_profile), NOT per /jobs request -- this does real per-entry
extraction work (SkillExtractor/TechnologyExtractor over every experience
and project entry), which is fine at save-time cadence but would be wasted,
repeated work if run on every job-list page load.

Deliberately zero LLM calls: role strength is a deterministic keyword-
coverage ratio against a small, generic role taxonomy (ROLE_TAXONOMY below),
using the SAME canonical skill/technology extractors (skills.json,
technologies.json, TrieMatcher) the JD-side jie/ pipeline already uses --
reused, not duplicated, per the standing instruction throughout this
project not to build a second competing extraction system.

Two separate concepts, never conflated:
  - capability.role_profiles: what the candidate's actual background
    supports, computed from experience + projects + skills. A strength of
    0.9 means "strong evidence", not "90% chance of getting hired."
  - intent: what the candidate actually wants, from explicit preference
    only (profile_data.career_preferences.desired_role, the same field
    jie/candidate_profile.py's CandidateProfile.from_profile_data already
    reads for target_roles -- reused here directly, not reinvented). Left
    empty/null if the candidate never set it. Capability is never copied
    into intent as a stand-in for a real preference.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.discovery.jie.extractors.skills import SkillExtractor
from src.discovery.jie.extractors.technologies import TechnologyExtractor

# Generic, reusable across any candidate -- not specific to any one
# person's actual role history. Each role's keywords are matched
# case-insensitively as substrings against extracted skills/technologies
# and raw entry text; this is intentionally a small, legible starter set
# (extend as new roles/keywords prove necessary against real profiles),
# not an attempt at an exhaustive taxonomy.
ROLE_TAXONOMY: Dict[str, List[str]] = {
    "AI Engineer": [
        "ai", "llm", "large language model", "machine learning", "ml",
        "rag", "retrieval-augmented generation", "langgraph", "langchain",
        "embeddings", "vector database", "pgvector", "prompt engineering",
        "nlp", "deep learning", "multi-agent",
    ],
    "Software Engineer": [
        "software engineer", "backend", "api", "microservices",
        "system design", "distributed systems", "rest api",
    ],
    "SDE": [
        "sde", "software development engineer", "data structures",
        "algorithms", "distributed systems",
    ],
    "Backend Engineer": [
        "backend", "api", "database", "server", "postgresql", "sql",
        "microservices", "redis",
    ],
    "Full Stack Engineer": [
        "full stack", "full-stack", "frontend", "react", "backend",
        "typescript", "react native",
    ],
    "Frontend Engineer": [
        "frontend", "react", "ui", "ux", "css", "javascript", "typescript",
        "tailwind",
    ],
    "Data Analyst": [
        "data analyst", "sql", "analytics", "dashboard", "tableau",
        "power bi", "data visualization", "excel",
    ],
    "Product Manager": [
        "product manager", "roadmap", "product strategy", "user research",
        "stakeholder", "requirements", "go-to-market",
    ],
}

MIN_SUPPORTING_ENTRIES = 1  # a role needs at least this much real evidence to appear at all


def _extract_entry_terms(entry_text: str, skill_extractor: SkillExtractor, tech_extractor: TechnologyExtractor) -> set:
    if not entry_text or not entry_text.strip():
        return set()
    terms = set(t.lower() for t in skill_extractor.extract(entry_text))
    terms |= set(t.lower() for t in tech_extractor.extract(entry_text))
    return terms


def _entry_text(entry: Dict[str, Any]) -> str:
    parts = [
        entry.get("role") or entry.get("title") or "",
        entry.get("name") or "",
        entry.get("description") or "",
    ]
    bullets = entry.get("bullet_points")
    if isinstance(bullets, list):
        parts.extend(b for b in bullets if isinstance(b, str))
    return " ".join(p for p in parts if p)


def _role_match_score(entry_terms: set, entry_text_lower: str, keywords: List[str]) -> float:
    """Fraction of this role's keywords found in this one entry (via
    extracted canonical terms OR raw text substring match, since a role
    keyword like "system design" is a technique/phrase the extractors
    don't canonicalize as a skill/technology, not something to miss just
    because it isn't in skills.json/technologies.json)."""
    if not keywords:
        return 0.0
    matched = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in entry_terms or kw_lower in entry_text_lower:
            matched += 1
    return matched / len(keywords)


def compute_role_profiles(profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Returns capability.role_profiles: a list of {role, strength,
    supporting_skills, supporting_experience, supporting_projects,
    evidence}, sorted by strength descending. Only roles with at least
    MIN_SUPPORTING_ENTRIES pieces of real evidence are included -- a role
    with zero supporting entries is not "weak evidence", it's no evidence,
    and shouldn't appear at all."""
    profile_data = profile_data or {}
    skill_extractor = SkillExtractor()
    tech_extractor = TechnologyExtractor()

    experience = profile_data.get("experience") or []
    projects = profile_data.get("projects") or []

    # Per-entry: (kind, label, terms, text_lower)
    entries: List[tuple] = []
    for exp in experience:
        label = exp.get("role") or exp.get("title") or exp.get("company") or "Experience"
        text = _entry_text(exp)
        entries.append(("experience", label, _extract_entry_terms(text, skill_extractor, tech_extractor), text.lower()))
    for proj in projects:
        label = proj.get("name") or proj.get("title") or "Project"
        text = _entry_text(proj)
        entries.append(("project", label, _extract_entry_terms(text, skill_extractor, tech_extractor), text.lower()))

    role_profiles: List[Dict[str, Any]] = []
    for role, keywords in ROLE_TAXONOMY.items():
        supporting_experience: List[str] = []
        supporting_projects: List[str] = []
        matched_keywords: set = set()
        entry_scores: List[float] = []

        for kind, label, terms, text_lower in entries:
            score = _role_match_score(terms, text_lower, keywords)
            if score <= 0:
                continue
            entry_scores.append(score)
            for kw in keywords:
                if kw.lower() in terms or kw.lower() in text_lower:
                    matched_keywords.add(kw)
            if kind == "experience":
                supporting_experience.append(label)
            else:
                supporting_projects.append(label)

        num_supporting = len(supporting_experience) + len(supporting_projects)
        if num_supporting < MIN_SUPPORTING_ENTRIES:
            continue

        # Overall role coverage: how much of the role's keyword set is
        # actually evidenced across ALL entries combined (not just one) --
        # a candidate whose evidence collectively covers most of a role's
        # keyword set scores higher than one with a single strong entry
        # but nothing else.
        coverage = len(matched_keywords) / len(keywords) if keywords else 0.0
        strength = round(min(1.0, coverage), 2)

        role_profiles.append({
            "role": role,
            "strength": strength,
            "supporting_skills": sorted(matched_keywords),
            "supporting_experience": supporting_experience,
            "supporting_projects": supporting_projects,
            "evidence": [f"{kw}" for kw in sorted(matched_keywords)],
        })

    role_profiles.sort(key=lambda r: r["strength"], reverse=True)
    return role_profiles


def compute_intent(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Intent is ONLY ever explicit user preference -- never inferred from
    capability. Reuses the exact same field
    jie/candidate_profile.py::CandidateProfile.from_profile_data already
    reads (profile_data.career_preferences.desired_role) rather than
    defining a second, competing preference field. Returns an empty/null
    shape if the candidate has never set this -- that's a real, honest
    "no preference captured yet" state, not something to backfill from
    resume content."""
    prefs = (profile_data or {}).get("career_preferences") or {}
    desired_role_raw = (prefs.get("desired_role") or "").strip()
    preferred_roles = [r.strip() for r in desired_role_raw.split(",") if r.strip()] if desired_role_raw else []

    return {
        "preferred_roles": preferred_roles,
        "excluded_roles": [],
        "preferences": {
            "locations": prefs.get("locations") or None,
            "work_type": prefs.get("work_type") or None,
            "min_salary": prefs.get("min_salary") or None,
            "open_to_relocation": prefs.get("open_to_relocation"),
        },
    }


def build_structured_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level entry point -- see api/routers/candidate.py's call site
    (gated behind ENABLE_STRUCTURED_CANDIDATE_PROFILE)."""
    return {
        "capability": {
            "role_profiles": compute_role_profiles(profile_data),
        },
        "intent": compute_intent(profile_data),
    }
