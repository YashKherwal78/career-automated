"""
Deterministic 1-page fit optimizer, implementing
resume_knowledge/rules/page_budget.yaml exactly:

  compression_passes_in_order:
    - bullet_compression        (hard-truncate over-long bullet text)
    - remove_weakest_bullets    (trim to per-section budget, weakest first, via bullet_scoring)
    - truncate_summary          (shorten, never delete)
    - compress_skills_formatting
    - format_tweaks_last_resort (font/margin, within bounds — never below min_font_pt)

  never_do:
    - delete a full experience/project/custom-section entry
    - shrink font below min_font_pt

No LLM calls anywhere in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from src.resume_intelligence.base_resume.bullet_scoring import rank_bullet_indices
from src.resume_intelligence.compiler.jake_resume.extended_models import ExtendedStructuredResume

SUMMARY_MAX_WORDS = 45  # ~3 lines at this template's font size/column width
EXPERIENCE_BULLETS_TOTAL_BUDGET = 8
PROJECT_BULLETS_TOTAL_BUDGET = 5
CUSTOM_SECTION_BULLETS_TOTAL_BUDGET = 5
MAX_BULLET_WORDS = 28  # matches engine_v1's own hard constraint, kept consistent

MIN_FONT_PT = 10.0
DEFAULT_FONT_PT = 10.5
MIN_MARGIN_IN = 0.5
DEFAULT_MARGIN_IN = 0.75


@dataclass
class RenderSettings:
    font_pt: float = DEFAULT_FONT_PT
    margin_in: float = DEFAULT_MARGIN_IN


@dataclass
class PageFitReport:
    passes_applied: List[str] = field(default_factory=list)
    final_page_count: int = 1
    fit_achieved: bool = True
    reason: str = ""


PageMeasurer = Callable[[ExtendedStructuredResume, RenderSettings], int]


def _truncate_bullet(text: str, max_words: int = MAX_BULLET_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"


def _truncate_summary(text: str, max_words: int = SUMMARY_MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    last_period = truncated.rfind(".")
    if last_period > max_words * 3:  # keep a full sentence if one comfortably fits
        return truncated[: last_period + 1]
    return truncated.rstrip(",.;:") + "…"


def _trim_section_bullets_to_budget(entries, total_budget: int) -> bool:
    """
    Trims bullets across a list of (company/project/custom) entries down to a
    combined total budget, removing the weakest bullets first (per
    bullet_scoring), never taking any single entry below 1 bullet. Returns
    True if any trimming happened.
    """
    total = sum(len(e.bullets) for e in entries)
    if total <= total_budget:
        return False

    changed = False
    # Repeatedly drop the single weakest bullet across all entries (that still
    # has more than 1 bullet) until we're within budget.
    while sum(len(e.bullets) for e in entries) > total_budget:
        worst_entry = None
        worst_score = None
        worst_idx = None
        for entry in entries:
            if len(entry.bullets) <= 1:
                continue  # never_do: don't empty an entry out entirely
            ranked = rank_bullet_indices(entry.bullets)
            candidate_idx = ranked[0]
            from src.resume_intelligence.base_resume.bullet_scoring import score_bullet
            candidate_score = score_bullet(entry.bullets[candidate_idx])
            if worst_score is None or candidate_score < worst_score:
                worst_score = candidate_score
                worst_entry = entry
                worst_idx = candidate_idx
        if worst_entry is None:
            break  # every entry is already down to 1 bullet — can't trim further
        del worst_entry.bullets[worst_idx]
        changed = True
    return changed


def optimize_for_one_page(
    resume: ExtendedStructuredResume,
    measure_page_count: PageMeasurer,
) -> tuple[ExtendedStructuredResume, RenderSettings, PageFitReport]:
    settings = RenderSettings()
    report = PageFitReport()

    page_count = measure_page_count(resume, settings)
    if page_count <= 1:
        report.final_page_count = page_count
        return resume, settings, report

    # Pass 1: bullet_compression — hard-truncate over-long bullet text.
    any_truncated = False
    for exp in resume.experience:
        exp.bullets = [_truncate_bullet(b) for b in exp.bullets]
    for proj in resume.projects:
        proj.bullets = [_truncate_bullet(b) for b in proj.bullets]
    for sec in resume.custom_sections:
        for item in sec.items:
            item.bullets = [_truncate_bullet(b) for b in item.bullets]
    report.passes_applied.append("bullet_compression")

    page_count = measure_page_count(resume, settings)
    if page_count <= 1:
        report.final_page_count = page_count
        return resume, settings, report

    # Pass 2: remove_weakest_bullets — trim to per-section budgets.
    _trim_section_bullets_to_budget(resume.experience, EXPERIENCE_BULLETS_TOTAL_BUDGET)
    _trim_section_bullets_to_budget(resume.projects, PROJECT_BULLETS_TOTAL_BUDGET)
    for sec in resume.custom_sections:
        _trim_section_bullets_to_budget(sec.items, CUSTOM_SECTION_BULLETS_TOTAL_BUDGET)
    report.passes_applied.append("remove_weakest_bullets")

    page_count = measure_page_count(resume, settings)
    if page_count <= 1:
        report.final_page_count = page_count
        return resume, settings, report

    # Pass 3: truncate_summary — shorten, never delete.
    if resume.summary:
        resume.summary = _truncate_summary(resume.summary)
        report.passes_applied.append("truncate_summary")

    page_count = measure_page_count(resume, settings)
    if page_count <= 1:
        report.final_page_count = page_count
        return resume, settings, report

    # Pass 4: compress_skills_formatting — cap items shown per category.
    MAX_SKILLS_PER_CATEGORY = 8
    for cat in resume.skill_categories:
        if len(cat.skills) > MAX_SKILLS_PER_CATEGORY:
            cat.skills = cat.skills[:MAX_SKILLS_PER_CATEGORY]
    report.passes_applied.append("compress_skills_formatting")

    page_count = measure_page_count(resume, settings)
    if page_count <= 1:
        report.final_page_count = page_count
        return resume, settings, report

    # Pass 5: format_tweaks_last_resort — font/margin, bounded, font never below MIN_FONT_PT.
    for font_pt, margin_in in ((10.0, 0.6), (MIN_FONT_PT, MIN_MARGIN_IN)):
        settings.font_pt = max(font_pt, MIN_FONT_PT)
        settings.margin_in = max(margin_in, MIN_MARGIN_IN)
        report.passes_applied.append(f"format_tweaks_last_resort(font={settings.font_pt}pt,margin={settings.margin_in}in)")
        page_count = measure_page_count(resume, settings)
        if page_count <= 1:
            report.final_page_count = page_count
            return resume, settings, report

    # Fallback: all passes exhausted, still >1 page. Ship as-is rather than
    # deleting entries (which never_do explicitly forbids) — log why.
    report.final_page_count = page_count
    report.fit_achieved = False
    report.reason = (
        f"Content still spans {page_count} pages after all compression passes "
        "without deleting any experience/project/custom-section entry, per "
        "page_budget.yaml's never_do rule."
    )
    return resume, settings, report
