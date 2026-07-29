"""
Orchestrates base-resume generation: profile_data -> ExtendedStructuredResume
-> 1-page-fit optimization -> Jake's Resume .tex (+ .pdf if pdflatex is
available). Zero LLM calls anywhere in this path.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from src.resume_intelligence.base_resume.builder import build_structured_resume
from src.resume_intelligence.base_resume.page_fit import optimize_for_one_page, PageFitReport, RenderSettings
from src.resume_intelligence.base_resume.renderer import compile_pdf, count_pdf_pages, render_tex

logger = logging.getLogger("BaseResumeGenerator")

BASE_RESUME_STORAGE_DIR = os.path.join("artifacts", "stored_base_resumes_json")


def _make_measurer():
    """
    Render -> compile -> count-pages closure for the page-fit optimizer.
    Uses a scratch temp dir per measurement so mid-optimization renders never
    touch the candidate's actual stored files. Falls back to "fits on 1 page"
    if pdflatex isn't available, since that's the best assumption we can make
    without a working compiler rather than looping forever.
    """

    def measure(resume, settings: RenderSettings) -> int:
        tex_content = render_tex(resume, settings)
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = compile_pdf(tex_content, tmp_dir, filename_prefix="measure")
            if pdf_path is None:
                logger.warning("pdflatex unavailable or compile failed during page-fit measurement — assuming 1 page")
                return 1
            return count_pdf_pages(pdf_path)

    return measure


def generate_base_resume(
    candidate_id: str,
    profile_data: Dict[str, Any],
) -> Tuple[str, Optional[str], PageFitReport]:
    """
    Returns (tex_content, pdf_path_or_None, page_fit_report). Writes the final
    .tex (and .pdf, if pdflatex is available) to this candidate's storage dir —
    the exact path tailor.py's _load_base_tex already expects.
    """
    resume = build_structured_resume(profile_data)
    optimized_resume, settings, report = optimize_for_one_page(resume, _make_measurer())

    tex_content = render_tex(optimized_resume, settings)

    out_dir = os.path.join(BASE_RESUME_STORAGE_DIR, candidate_id)
    os.makedirs(out_dir, exist_ok=True)
    tex_path = os.path.join(out_dir, "base_resume.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)

    pdf_path = compile_pdf(tex_content, out_dir, filename_prefix="base_resume")

    logger.info(
        "Generated base resume for candidate_id=%s: passes=%s fit_achieved=%s pages=%s",
        candidate_id, report.passes_applied, report.fit_achieved, report.final_page_count,
    )

    return tex_content, pdf_path, report
