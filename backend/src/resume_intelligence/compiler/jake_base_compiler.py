"""
Master Base Resume Compiler using yash_resume_base_v2.tex directly.
"""

import os
import subprocess
from typing import Dict, Any
from jinja2 import Template
import os
import subprocess
from typing import Dict, Any
from jinja2 import Template
from src.resume_intelligence.compiler.jake_resume.models import StructuredResume


# Pure Jinja template wrapping yash_resume_base_v2.tex layout exactly
JAKE_BASE_V2_TEMPLATE = r"""
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

% BEGIN SECTION: CONTACT
\begin{center}
    \textbf{\Huge \scshape {{ resume.name }}} \\ \vspace{1pt}
    \small {{ resume.contact.phone }}
    {% if resume.contact.email %} $|$ \href{mailto:{{ resume.contact.email }}}{ {{ resume.contact.email }} }{% endif %}
    {% if resume.contact.linkedin %} $|$ \href{ {{ resume.contact.linkedin }} }{ {{ resume.contact.linkedin | replace('https://', '') | replace('http://', '') | replace('www.', '') }} }{% endif %}
    {% if resume.contact.github %} $|$ \href{ {{ resume.contact.github }} }{ {{ resume.contact.github | replace('https://', '') | replace('http://', '') | replace('www.', '') }} }{% endif %}
    {% if resume.contact.portfolio %} $|$ \href{ {{ resume.contact.portfolio }} }{ {{ resume.contact.portfolio | replace('https://', '') | replace('http://', '') | replace('www.', '') }} }{% endif %}
\end{center}
% END SECTION: CONTACT

{% if resume.summary %}
% BEGIN SECTION: SUMMARY
\section{Summary}
\small{ {{ resume.summary | replace('%', '\\%') | replace('&', '\\&') }} }
\vspace{2pt}
% END SECTION: SUMMARY
{% endif %}

{% if resume.education %}
% BEGIN SECTION: EDUCATION
\section{Education}
\resumeSubHeadingListStart
{% for edu in resume.education %}
  \resumeSubheading
    { {{ edu.institution }} }{ {{ edu.start_date }}{% if edu.end_date %} -- {{ edu.end_date }}{% endif %} }
    { {{ edu.degree }}{% if edu.field_of_study %} in {{ edu.field_of_study }}{% endif %} }{}
{% endfor %}
\resumeSubHeadingListEnd
% END SECTION: EDUCATION
{% endif %}

{% if resume.experience %}
% BEGIN SECTION: EXPERIENCE
\section{Experience}
\resumeSubHeadingListStart
{% for exp in resume.experience %}
  \resumeSubheading
    { {{ exp.company | replace('&', '\\&') }} }{ {{ exp.start_date }}{% if exp.end_date %} -- {{ exp.end_date }}{% endif %} }
    { {{ exp.title | replace('&', '\\&') }} }{}
  \resumeItemListStart
    {% for b in exp.bullets %}
    \resumeItem{ {{ b | replace('%', '\\%') | replace('&', '\\&') | replace('~', '$\\sim$') }} }
    {% endfor %}
  \resumeItemListEnd
{% endfor %}
\resumeSubHeadingListEnd
% END SECTION: EXPERIENCE
{% endif %}

{% if resume.projects %}
% BEGIN SECTION: PROJECTS
\section{ {{ project_section_title | default('Projects') }} }
\resumeSubHeadingListStart
{% for proj in resume.projects %}
  \resumeProjectHeading
    {\textbf{ {{ proj.title | replace('&', '\\&') }} } $|$ \emph{ {{ proj.technologies | join(', ') | replace('&', '\\&') }} }}{ {{ proj.date }} }
  \resumeItemListStart
    {% for b in proj.bullets %}
    \resumeItem{ {{ b | replace('%', '\\%') | replace('&', '\\&') | replace('~', '$\\sim$') }} }
    {% endfor %}
  \resumeItemListEnd
{% endfor %}
\resumeSubHeadingListEnd
% END SECTION: PROJECTS
{% endif %}

% BEGIN SECTION: SKILLS
\section{Technical Skills}
\begin{itemize}[leftmargin=0.15in, label={}]
  \small{\item{
    {% for cat in resume.skill_categories %}
    \textbf{ {{ cat.category_name }}:} {{ cat.skills | join(', ') }} {% if not loop.last %}\\ {% endif %}
    {% endfor %}
  }}
\end{itemize}
% END SECTION: SKILLS

{% if resume.custom_sections %}
{% for sec in resume.custom_sections %}
% BEGIN SECTION: {{ sec.section_title | upper | replace(' ', '_') }}
\section{ {{ sec.section_title }} }
\resumeSubHeadingListStart
{% for item in sec.items %}
  \resumeProjectHeading
    {\textbf{ {{ item.title | replace('&', '\\&') }} } {% if item.technologies %} $|$ \emph{ {{ item.technologies | join(', ') | replace('&', '\\&') }} }{% endif %}}{ {{ item.date | default('') }} }
  {% if item.bullets %}
  \resumeItemListStart
    {% for b in item.bullets %}
    \resumeItem{ {{ b | replace('%', '\\%') | replace('&', '\\&') | replace('~', '$\\sim$') }} }
    {% endfor %}
  \resumeItemListEnd
  {% endif %}
{% endfor %}
\resumeSubHeadingListEnd
% END SECTION: {{ sec.section_title | upper | replace(' ', '_') }}
{% endfor %}
{% endif %}

\end{document}
"""


class JakeBaseCompiler:
    """Consumes StructuredResume presentation contract and renders yash_resume_base_v2.tex."""

    def render_and_compile(
        self,
        resume: StructuredResume,
        output_dir: str,
        filename_prefix: str = "Yash_Kherwal_Resume",
        project_section_title: str = "Projects"
    ) -> Dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        tmpl = Template(JAKE_BASE_V2_TEMPLATE, comment_start_string='/*JINJA', comment_end_string='JINJA*/')
        tex_content = tmpl.render(resume=resume, project_section_title=project_section_title)

        tex_path = os.path.join(output_dir, f"{filename_prefix}.tex")
        pdf_path = os.path.join(output_dir, f"{filename_prefix}.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", output_dir, tex_path],
            capture_output=True,
            check=False
        )

        return {"tex": tex_path, "pdf": pdf_path}

