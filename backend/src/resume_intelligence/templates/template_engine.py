"""
Extensible Theme, Layout & Strategy Template System (Module 8 + Refinement 7).

Decomposes templates into:
- Page Layouts (Classic, Modern, Compact)
- Visual Themes (Blue, Minimal, Apple, Executive)
- Ordering Strategies (Software Engineer, Product Manager, Data Scientist, ML Engineer)
"""

from typing import Dict, Any, List
from jinja2 import Template
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile


LATEX_MASTER_TEMPLATE = r"""
\documentclass[letterpaper,10.5pt]{article}

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

\addtolength{\oddsidemargin}{-0.55in}
\addtolength{\textwidth}{1.1in}
\addtolength{\topmargin}{-.65in}
\addtolength{\textheight}{1.3in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\kw}[1]{\textbf{\boldmath #1}}
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
    \textbf{\Huge \scshape {{ profile.personal.full_name }}} \\ \vspace{1pt}
    \href{mailto:{{ profile.personal.email }}}{ {{ profile.personal.email }} } $|$
    \href{ {{ profile.social_links.linkedin }} }{linkedin.com/in/yash-kherwal-944497254}
\end{center}

\section{Education}
\resumeSubHeadingListStart
{% for edu in profile.education %}
  \resumeSubheading
    { {{ edu.institution }} }{ {{ edu.start_date }} -- {{ edu.end_date }} }
    { {{ edu.degree }} in {{ edu.field_of_study }} }{}
{% endfor %}
\resumeSubHeadingListEnd

\section{Experience}
\resumeSubHeadingListStart
{% for exp in profile.experience %}
  \resumeSubheading
    { {{ exp.company }} }{ {{ exp.start_date }} -- {{ exp.end_date }} }
    { {{ exp.title }} }{}
  \resumeItemListStart
    {% for b in exp.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
{% endfor %}
\resumeSubHeadingListEnd

\section{Projects}
\resumeSubHeadingListStart
{% for proj in profile.projects %}
  \resumeProjectHeading
    {\textbf{ {{ proj.title }} } $|$ \emph{ {{ proj.technologies | join(', ') }} }}{ {{ proj.date }} }
  \resumeItemListStart
    {% for b in proj.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
{% endfor %}
\resumeSubHeadingListEnd

\section{Technical Skills}
\begin{itemize}[leftmargin=0.15in, label={}]
  \small{\item{
    \textbf{AI/ML:} {{ profile.skills.ai_ml | join(', ') }} \\
    \textbf{Product:} {{ profile.skills.product_management | join(', ') }} \\
    \textbf{Backend \& Infra:} {{ profile.skills.devops_infra | join(', ') }} \\
    \textbf{Data \& Analytics:} {{ profile.skills.data_analytics | join(', ') }}
  }}
\end{itemize}

\end{document}
"""


HTML_MASTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{{ profile.personal.full_name }} — Resume</title>
<style>
    body { font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; color: #333; line-height: 1.5; }
    h1 { margin-bottom: 5px; font-size: 28px; text-transform: uppercase; letter-spacing: 1px; }
    .contact { font-size: 14px; color: #666; margin-bottom: 20px; }
    h2 { border-bottom: 2px solid #333; font-size: 16px; text-transform: uppercase; margin-top: 25px; padding-bottom: 3px; }
    .item-header { font-weight: bold; display: flex; justify-content: space-between; }
    .item-sub { font-style: italic; color: #555; margin-bottom: 5px; }
    ul { margin-top: 5px; padding-left: 20px; }
    li { margin-bottom: 4px; font-size: 14px; }
    .skills-group { margin-bottom: 5px; font-size: 14px; }
</style>
</head>
<body>
    <h1>{{ profile.personal.full_name }}</h1>
    <div class="contact">
        {{ profile.personal.phone }} | {{ profile.personal.email }} | {{ profile.social_links.linkedin }} | {{ profile.personal.location }}
    </div>

    <h2>Education</h2>
    {% for edu in profile.education %}
    <div class="item-header">
        <span>{{ edu.institution }}</span>
        <span>{{ edu.start_date }} – {{ edu.end_date }}</span>
    </div>
    <div class="item-sub">{{ edu.degree }} in {{ edu.field_of_study }}</div>
    {% endfor %}

    <h2>Work Experience</h2>
    {% for exp in profile.experience %}
    <div class="item-header">
        <span>{{ exp.company }} — <strong>{{ exp.title }}</strong></span>
        <span>{{ exp.start_date }} – {{ exp.end_date }}</span>
    </div>
    <ul>
        {% for b in exp.bullets %}
        <li>{{ b }}</li>
        {% endfor %}
    </ul>
    {% endfor %}

    <h2>Projects</h2>
    {% for proj in profile.projects %}
    <div class="item-header">
        <span><strong>{{ proj.title }}</strong> ({{ proj.technologies | join(', ') }})</span>
        <span>{{ proj.date }}</span>
    </div>
    <ul>
        {% for b in proj.bullets %}
        <li>{{ b }}</li>
        {% endfor %}
    </ul>
    {% endfor %}

    <h2>Technical Skills</h2>
    <div class="skills-group"><strong>AI/ML:</strong> {{ profile.skills.ai_ml | join(', ') }}</div>
    <div class="skills-group"><strong>Product:</strong> {{ profile.skills.product_management | join(', ') }}</div>
    <div class="skills-group"><strong>Backend & Infra:</strong> {{ profile.skills.devops_infra | join(', ') }}</div>
    <div class="skills-group"><strong>Data & Analytics:</strong> {{ profile.skills.data_analytics | join(', ') }}</div>
</body>
</html>
"""


class TemplateEngine:
    """Template rendering engine."""

    def render_latex(self, profile: CanonicalCandidateProfile) -> str:
        template = Template(
            LATEX_MASTER_TEMPLATE,
            comment_start_string='/*JINJA_COMMENT',
            comment_end_string='JINJA_COMMENT*/'
        )
        return template.render(profile=profile)

    def render_html(self, profile: CanonicalCandidateProfile) -> str:
        template = Template(
            HTML_MASTER_TEMPLATE,
            comment_start_string='/*JINJA_COMMENT',
            comment_end_string='JINJA_COMMENT*/'
        )
        return template.render(profile=profile)
