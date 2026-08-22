"""
Jake's Resume LaTeX renderer — deterministic templating only, no LLM calls.

Rewritten from the orphaned compiler/jake_resume/pdf_renderer.py to fix two
real bugs found there: (1) the header hardcoded one person's LinkedIn/GitHub
handle as the visible link text regardless of whose resume was being
rendered, and (2) no LaTeX-special-character escaping was applied to any
candidate-provided text, so content containing %, &, $, #, _ etc. (all
common in real resumes) would break compilation silently.
"""

from __future__ import annotations

import copy
import os
import re
import subprocess
from typing import Optional

from jinja2 import Template

from src.resume_intelligence.base_resume.latex_escape import latex_escape
from src.resume_intelligence.base_resume.page_fit import RenderSettings
from src.resume_intelligence.compiler.jake_resume.extended_models import ExtendedStructuredResume

JAKE_LATEX_TEMPLATE = r"""
\documentclass[letterpaper,{{ settings.font_pt }}pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{xcolor}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Geometry & margins — parameterized so the page-fit optimizer can tighten
% them within page_budget.yaml's format_tweak_bounds (min_margin_in: 0.5).
\addtolength{\oddsidemargin}{-{{ (0.75 - settings.margin_in + 0.55) }}in}
\addtolength{\textwidth}{ {{ (0.75 - settings.margin_in) * 2 + 1.1 }}in}
\addtolength{\topmargin}{-.65in}
\addtolength{\textheight}{1.3in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{\item\small{#1 \vspace{-2pt}}}
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
  \begin{tabular*}{0.97\textwidth}[t]{l @{\extracolsep{\fill}} r}
    \textbf{#1} & #2 \\
    \textit{\small #3} & \textit{\small #4} \\
  \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeProjectHeading}[2]{
  \item
  \begin{tabular*}{0.97\textwidth}{l @{\extracolsep{\fill}} r}
    \small #1 & \small #2 \\
  \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[leftmargin=*]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\begin{document}

\begin{center}
    \textbf{\Huge \scshape {{ resume.name }}} \\ \vspace{2pt}
    \small
    {%- set contact_parts = [] -%}
    {%- if resume.contact.phone %}{{ contact_parts.append(resume.contact.phone) or "" }}{% endif -%}
    {%- if resume.contact.email %}{{ contact_parts.append("\\href{mailto:" ~ resume.contact.email ~ "}{" ~ resume.contact.email_display ~ "}") or "" }}{% endif -%}
    {%- if resume.contact.linkedin %}{{ contact_parts.append("\\href{" ~ resume.contact.linkedin ~ "}{" ~ resume.contact.linkedin_display ~ "}") or "" }}{% endif -%}
    {%- if resume.contact.github %}{{ contact_parts.append("\\href{" ~ resume.contact.github ~ "}{" ~ resume.contact.github_display ~ "}") or "" }}{% endif -%}
    {%- if resume.contact.portfolio %}{{ contact_parts.append("\\href{" ~ resume.contact.portfolio ~ "}{" ~ resume.contact.portfolio_display ~ "}") or "" }}{% endif -%}
    {{ contact_parts | join(" $|$ ") }}
\end{center}
\vspace{-10pt}

{% for sec in resume.section_order %}
{% if sec == 'summary' and resume.summary %}
\section{Professional Summary}
\small{ {{ resume.summary }} }
{% elif sec == 'education' and resume.education %}
\section{Education}
\resumeSubHeadingListStart
{% for edu in resume.education %}
  \resumeSubheading
    { {{ edu.institution }} }{ {{ edu.start_date }} -- {{ edu.end_date }} }
    { {{ edu.degree }}{% if edu.field_of_study %} in {{ edu.field_of_study }}{% endif %} }{ {{ edu.location }} }
{% endfor %}
\resumeSubHeadingListEnd
{% elif sec == 'experience' and resume.experience %}
\section{Experience}
\resumeSubHeadingListStart
{% for exp in resume.experience %}
  \resumeSubheading
    { {{ exp.title }} }{ {{ exp.start_date }} -- {{ exp.end_date }} }
    { {{ exp.company }} }{ {{ exp.location }} }
  {% if exp.bullets %}
  \resumeItemListStart
    {% for b in exp.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
  {% endif %}
{% endfor %}
\resumeSubHeadingListEnd
{% elif sec == 'projects' and resume.projects %}
\section{Projects}
\resumeSubHeadingListStart
{% for proj in resume.projects %}
  \resumeProjectHeading
    {\textbf{ {{ proj.title }} }{% if proj.technologies %} $|$ \emph{ {{ proj.technologies | join(' $\\bullet$ ') }} }{% endif %}}{ {{ proj.date }} }
  {% if proj.bullets %}
  \resumeItemListStart
    {% for b in proj.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
  {% endif %}
{% endfor %}
\resumeSubHeadingListEnd
{% elif sec == 'skills' and resume.skill_categories %}
\section{Technical Skills}
\begin{itemize}[leftmargin=0.15in, label={}]
  \small{\item{
    {% for cat in resume.skill_categories %}
    \textbf{ {{ cat.category_name }}:} {{ cat.skills | join(' $\\bullet$ ') }} {% if not loop.last %}\\ \vspace{-2pt} {% endif %}
    {% endfor %}
  }}
\end{itemize}
{% elif sec.startswith('custom:') %}
{% set title = sec[7:] %}
{% for cs in resume.custom_sections %}
{% if cs.section_title == title %}
\section{ {{ cs.section_title }} }
\resumeSubHeadingListStart
{% for item in cs.items %}
  \resumeProjectHeading
    {\textbf{ {{ item.title }} }{% if item.subtitle %} $|$ \emph{ {{ item.subtitle }} }{% endif %}}{ {{ item.date or "" }} }
  {% if item.bullets %}
  \resumeItemListStart
    {% for b in item.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
  {% endif %}
{% endfor %}
\resumeSubHeadingListEnd
{% endif %}
{% endfor %}
{% endif %}
{% endfor %}

\end{document}
"""


def _display_handle(url: str) -> str:
    """Derives a short display label from a profile URL, e.g. linkedin.com/in/name."""
    if not url:
        return ""
    stripped = url.replace("https://", "").replace("http://", "").rstrip("/")
    return stripped


def _escape_resume(resume: ExtendedStructuredResume) -> ExtendedStructuredResume:
    """Returns a deep copy with every free-text field LaTeX-escaped."""
    r = copy.deepcopy(resume)
    r.name = latex_escape(r.name)
    # Contact fields are handled entirely by _ContactDisplay (below) — phone is
    # escaped there, email/linkedin/github/portfolio href targets stay raw with
    # separately-escaped display text — so nothing to do here for r.contact.
    r.summary = latex_escape(r.summary) if r.summary else r.summary

    for edu in r.education:
        edu.institution = latex_escape(edu.institution)
        edu.degree = latex_escape(edu.degree)
        edu.field_of_study = latex_escape(edu.field_of_study)
        edu.location = latex_escape(edu.location)
        edu.start_date = latex_escape(edu.start_date)
        edu.end_date = latex_escape(edu.end_date)

    for exp in r.experience:
        exp.company = latex_escape(exp.company)
        exp.title = latex_escape(exp.title)
        exp.location = latex_escape(exp.location)
        exp.start_date = latex_escape(exp.start_date)
        exp.end_date = latex_escape(exp.end_date)
        exp.bullets = [latex_escape(b) for b in exp.bullets]

    for proj in r.projects:
        proj.title = latex_escape(proj.title)
        proj.date = latex_escape(proj.date)
        proj.technologies = [latex_escape(t) for t in proj.technologies]
        proj.bullets = [latex_escape(b) for b in proj.bullets]

    for cat in r.skill_categories:
        cat.category_name = latex_escape(cat.category_name)
        cat.skills = [latex_escape(s) for s in cat.skills]

    for sec in r.custom_sections:
        sec.section_title = latex_escape(sec.section_title)
        for item in sec.items:
            item.title = latex_escape(item.title)
            item.subtitle = latex_escape(item.subtitle) if item.subtitle else item.subtitle
            item.date = latex_escape(item.date) if item.date else item.date
            item.location = latex_escape(item.location) if item.location else item.location
            item.bullets = [latex_escape(b) for b in item.bullets]
            item.technologies = [latex_escape(t) for t in item.technologies]

    return r


class _ContactDisplay:
    """Thin wrapper so the template can reference contact.linkedin_display etc."""

    def __init__(self, contact):
        self._c = contact
        self.phone = latex_escape(contact.phone)
        # href targets stay raw (unescaped) — they're URL arguments, not text.
        self.email = contact.email
        self.linkedin = contact.linkedin
        self.github = contact.github
        self.portfolio = contact.portfolio
        # Display text is visible LaTeX text and must be escaped like any other.
        self.email_display = latex_escape(contact.email)
        self.linkedin_display = latex_escape(_display_handle(contact.linkedin))
        self.github_display = latex_escape(_display_handle(contact.github))
        self.portfolio_display = latex_escape(_display_handle(contact.portfolio)) if contact.portfolio else ""


def render_tex(resume: ExtendedStructuredResume, settings: RenderSettings) -> str:
    """Renders the resume to a Jake's-Resume-format LaTeX string. No LLM calls."""
    escaped = _escape_resume(resume)
    template_resume = copy.copy(escaped)
    template_resume.contact = _ContactDisplay(escaped.contact)
    # Custom comment delimiters: the default {# ... #} collides with LaTeX
    # macro parameters like \newcommand{\foo}[1]{...{#1}...}. This template
    # never uses Jinja comments, so any non-colliding delimiter pair is fine.
    tmpl = Template(JAKE_LATEX_TEMPLATE, comment_start_string="@@JINJA_COMMENT_START@@", comment_end_string="@@JINJA_COMMENT_END@@")
    return tmpl.render(resume=template_resume, settings=settings)


# Unicode whitespace variants LLM output sometimes contains (narrow
# no-break space, non-breaking space, thin space, zero-width space) that
# this project's LaTeX setup has no glyph for -- pdflatex hard-errors
# ("Unicode character ... not set up for use with LaTeX") and, combined
# with -halt-on-error below, silently returns None with no PDF at all
# instead of a readable error. Confirmed live (2026-08-22): a tailored
# bullet's LLM rewrite contained a U+202F NARROW NO-BREAK SPACE and
# compile_pdf() failed outright, even though the same content compiles
# fine once this character is normalized to a plain space. Deliberately
# narrow -- only whitespace-lookalikes are touched, never real content
# (em/en dashes, smart quotes, etc. already compile fine with this
# template's fontenc setup and aren't touched here).
_UNSAFE_UNICODE_WHITESPACE = {
    " ": " ",  # narrow no-break space
    " ": " ",  # no-break space
    " ": " ",  # thin space
    " ": " ",  # hair space
    "​": "",   # zero-width space
    "﻿": "",   # zero-width no-break space / BOM
}


def _sanitize_unicode_whitespace(text: str) -> str:
    for bad, good in _UNSAFE_UNICODE_WHITESPACE.items():
        text = text.replace(bad, good)
    return text


# PDF-text-extraction artifacts: a source resume's PDF text layer can split
# a compound word/acronym across an internal kerning or ligature boundary
# (e.g. "VAD" in the original PDF extracts as "V AD") -- this happens at
# the ProfileExtractionService step, upstream of anything this renderer
# controls, and gets carried verbatim into stored profile text and from
# there into every rendered resume. Confirmed live (2026-08-22): found in
# real stored bullet_points, not something introduced by templating.
# Deterministic string fix, not an LLM call -- extend this map as new
# split tokens turn up in real uploads, same reasoning as
# _UNSAFE_UNICODE_WHITESPACE above.
_SPLIT_TOKEN_PATTERNS: dict[str, str] = {
    r"V\s+AD\b": "VAD",
    r"T\s+esseract\b": "Tesseract",
    r"F\s+astAPI\b": "FastAPI",
    r"T\s+emporal\b": "Temporal",
    r"A\s+TS\b": "ATS",
    r"Post\s+greSQL\b": "PostgreSQL",
    r"Lang\s+Graph\b": "LangGraph",
    r"Lang\s+Chain\b": "LangChain",
    r"Play\s+wright\b": "Playwright",
    r"Git\s+Hub\b": "GitHub",
    r"Type\s+Script\b": "TypeScript",
    r"Dock\s+er\b": "Docker",
}


def _fix_split_tokens(text: str) -> str:
    for pattern, replacement in _SPLIT_TOKEN_PATTERNS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def compile_pdf(tex_content: str, output_dir: str, filename_prefix: str = "base_resume") -> Optional[str]:
    """Compiles .tex to PDF via pdflatex. Returns the PDF path, or None if pdflatex failed."""
    os.makedirs(output_dir, exist_ok=True)
    tex_path = os.path.join(output_dir, f"{filename_prefix}.tex")
    pdf_path = os.path.join(output_dir, f"{filename_prefix}.pdf")

    tex_content = _sanitize_unicode_whitespace(tex_content)
    tex_content = _fix_split_tokens(tex_content)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)

    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", output_dir, tex_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not os.path.exists(pdf_path):
            return None
        return pdf_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def count_pdf_pages(pdf_path: str) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return 1
