"""
Cover letter .tex rendering + PDF compilation.

Deterministic templating only, no LLM calls — mirrors
base_resume/renderer.py's split (build a full .tex string, then compile it
with the same pdflatex wrapper) rather than inventing a second compilation
path. A cover letter has no existing visual style to preserve (it was
plain text before this), so the template here is a plain, standard
business-letter layout: sender block, date, greeting, body paragraphs,
sign-off — nothing borrowed from the resume template, since a resume and
a letter are different documents with different conventions.
"""
from __future__ import annotations

from src.resume_intelligence.base_resume.latex_escape import latex_escape
from src.resume_intelligence.base_resume.renderer import compile_pdf  # noqa: F401  (re-exported for callers)

_COVER_LETTER_TEMPLATE = r"""\documentclass[11pt]{{letter}}
\usepackage[utf8]{{inputenc}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{parskip}}

\signature{{{candidate_name}}}
\address{{{candidate_name}\\{contact_line}}}

\begin{{document}}
\begin{{letter}}{{{company_name}\\{role_title}}}

\opening{{Dear Hiring Team,}}

{body}

\closing{{Sincerely,}}

\end{{letter}}
\end{{document}}
"""


def render_cover_letter_tex(
    cover_letter_text: str,
    candidate_name: str,
    candidate_email: str,
    candidate_phone: str,
    company_name: str,
    role_title: str,
) -> str:
    """Builds a full, standalone .tex document from the generated letter
    text. Paragraphs (split on blank lines) become separate LaTeX
    paragraphs; every candidate/JD-sourced string is escaped since cover
    letter text routinely contains %, &, and other LaTeX-special
    characters (company names, technical terms) that would otherwise break
    compilation silently -- same risk base_resume/renderer.py's docstring
    already flagged for resumes."""
    # Escape each value individually -- escaping the joined string would
    # also mangle the literal "$\cdot$" separator markup itself (confirmed:
    # rendered as literal "$\cdot$" text in the PDF instead of a centered
    # dot, since latex_escape doesn't know that substring is markup, not
    # candidate data).
    contact_parts = [latex_escape(p) for p in (candidate_email, candidate_phone) if p]
    contact_line = " $\\cdot$ ".join(contact_parts)

    paragraphs = [p.strip() for p in cover_letter_text.split("\n\n") if p.strip()]
    body = "\n\n".join(latex_escape(p) for p in paragraphs)

    return _COVER_LETTER_TEMPLATE.format(
        candidate_name=latex_escape(candidate_name or "Candidate"),
        contact_line=contact_line,
        company_name=latex_escape(company_name or "Hiring Team"),
        role_title=latex_escape(role_title or ""),
        body=body,
    )
