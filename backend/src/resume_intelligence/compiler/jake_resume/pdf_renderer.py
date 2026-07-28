"""
Jake Resume PDF Renderer Subsystem — Authentic High-Density Implementation.

Matches Jake Gutierrez's exact typography, compact line heights, section spacing,
and right-aligned single-row project/experience metadata.
"""

import os
import subprocess
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from src.resume_intelligence.compiler.jake_resume.models import StructuredResume

JAKE_LATEX_TEMPLATE = r"""
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

% Exact Jake Gutierrez Geometry & Margins
\addtolength{\oddsidemargin}{-0.55in}
\addtolength{\textwidth}{1.1in}
\addtolength{\topmargin}{-.65in}
\addtolength{\textheight}{1.3in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Section Titles with Thin Rule
\titleformat{\section}{
  \vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

% Macros
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

% Header — Single Compact Line
\begin{center}
    \textbf{\Huge \scshape {{ resume.name }}} \\ \vspace{2pt}
    \small {{ resume.contact.phone }} $|$
    \href{mailto:{{ resume.contact.email }}}{ {{ resume.contact.email }} } $|$
    \href{ {{ resume.contact.linkedin }} }{linkedin.com/in/yash-kherwal-944497254} $|$
    \href{ {{ resume.contact.github }} }{github.com/YashKherwal78}
\end{center}
\vspace{-10pt}

% Dynamic Section Rendering Order
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
    { {{ edu.degree }} in {{ edu.field_of_study }} }{ {{ edu.location }} }
{% endfor %}
\resumeSubHeadingListEnd
{% elif sec == 'experience' and resume.experience %}
\section{Experience}
\resumeSubHeadingListStart
{% for exp in resume.experience %}
  \resumeSubheading
    { {{ exp.title }} }{ {{ exp.start_date }} -- {{ exp.end_date }} }
    { {{ exp.company }} }{ {{ exp.location }} }
  \resumeItemListStart
    {% for b in exp.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
{% endfor %}
\resumeSubHeadingListEnd
{% elif sec == 'projects' and resume.projects %}
\section{Projects}
\resumeSubHeadingListStart
{% for proj in resume.projects %}
  \resumeProjectHeading
    {\textbf{ {{ proj.title }} } $|$ \emph{ {{ proj.technologies | join(' $\\bullet$ ') }} }}{ {{ proj.date }} }
  \resumeItemListStart
    {% for b in proj.bullets %}
    \resumeItem{ {{ b }} }
    {% endfor %}
  \resumeItemListEnd
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
{% endif %}
{% endfor %}

\end{document}
"""


class JakePDFRenderer:
    """PDF Renderer for Jake Resume V1."""

    def render(self, resume: StructuredResume, pdf_path: str, tex_path: Optional[str] = None) -> str:
        out_dir = os.path.dirname(pdf_path)
        os.makedirs(out_dir, exist_ok=True)

        # 1. Try pdflatex if available
        if tex_path:
            try:
                from jinja2 import Template
                tmpl = Template(JAKE_LATEX_TEMPLATE, comment_start_string='/*JINJA', comment_end_string='JINJA*/')
                tex_content = tmpl.render(resume=resume)
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(tex_content)

                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", out_dir, tex_path],
                    capture_output=True,
                    check=False
                )
                if os.path.exists(pdf_path):
                    return pdf_path
            except Exception:
                pass

        # 2. Native ReportLab PDF Compiler (Fallback)
        return self._render_reportlab_pdf(resume, pdf_path)

    def _render_reportlab_pdf(self, resume: StructuredResume, pdf_path: str) -> str:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        story = []

        # Styles definition
        title_style = ParagraphStyle('JakeTitle', parent=styles['Heading1'], fontSize=18, leading=20, alignment=1, spaceAfter=2)
        contact_style = ParagraphStyle('JakeContact', parent=styles['Normal'], fontSize=9, leading=11, alignment=1, spaceAfter=6)
        sec_title_style = ParagraphStyle('JakeSecTitle', parent=styles['Heading2'], fontSize=10.5, leading=12, spaceBefore=4, spaceAfter=2, textTransform='uppercase')
        
        left_bold = ParagraphStyle('JakeLeftBold', parent=styles['Normal'], fontSize=9.5, leading=11, fontName='Helvetica-Bold')
        left_italic = ParagraphStyle('JakeLeftItalic', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Oblique')
        right_plain = ParagraphStyle('JakeRightPlain', parent=styles['Normal'], fontSize=9, leading=11, alignment=2)
        bullet_style = ParagraphStyle('JakeBullet', parent=styles['Normal'], fontSize=9, leading=11, leftIndent=10, firstLineIndent=-6, spaceAfter=1)
        skill_style = ParagraphStyle('JakeSkill', parent=styles['Normal'], fontSize=9, leading=11.5)

        # 1. Header
        story.append(Paragraph(f"<b>{resume.name.upper()}</b>", title_style))
        c_line = f"{resume.contact.phone}  |  {resume.contact.email}  |  {resume.contact.linkedin}  |  {resume.contact.github}"
        story.append(Paragraph(c_line, contact_style))

        # 2. Dynamic Section Ordering
        for sec in resume.section_order:
            if sec == "summary" and resume.summary:
                story.append(Paragraph("<b>PROFESSIONAL SUMMARY</b>", sec_title_style))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=1, spaceAfter=3))
                story.append(Paragraph(resume.summary, bullet_style))
                story.append(Spacer(1, 2))

            elif sec == "education" and resume.education:
                story.append(Paragraph("<b>EDUCATION</b>", sec_title_style))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=1, spaceAfter=3))
                for edu in resume.education:
                    t_data = [
                        [Paragraph(f"<b>{edu.institution}</b>", left_bold), Paragraph(f"{edu.start_date} – {edu.end_date}", right_plain)],
                        [Paragraph(f"<i>{edu.degree} in {edu.field_of_study}</i>", left_italic), Paragraph(f"<i>{edu.location}</i>", right_plain)]
                    ]
                    t = Table(t_data, colWidths=[380, 160])
                    t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                    story.append(t)
                story.append(Spacer(1, 2))

            elif sec == "experience" and resume.experience:
                story.append(Paragraph("<b>EXPERIENCE</b>", sec_title_style))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=1, spaceAfter=3))
                for exp in resume.experience:
                    t_data = [
                        [Paragraph(f"<b>{exp.title}</b>", left_bold), Paragraph(f"{exp.start_date} – {exp.end_date}", right_plain)],
                        [Paragraph(f"<i>{exp.company}</i>", left_italic), Paragraph(f"<i>{exp.location}</i>", right_plain)]
                    ]
                    t = Table(t_data, colWidths=[380, 160])
                    t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                    story.append(t)
                    for b in exp.bullets:
                        story.append(Paragraph(f"•  {b}", bullet_style))
                    story.append(Spacer(1, 1))

            elif sec == "projects" and resume.projects:
                story.append(Paragraph("<b>PROJECTS</b>", sec_title_style))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=1, spaceAfter=3))
                for proj in resume.projects:
                    tech_str = f"  |  <i>{' • '.join(proj.technologies)}</i>" if proj.technologies else ""
                    t_data = [
                        [Paragraph(f"<b>{proj.title}</b>{tech_str}", left_bold), Paragraph(f"{proj.date}", right_plain)]
                    ]
                    t = Table(t_data, colWidths=[420, 120])
                    t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
                    story.append(t)
                    for b in proj.bullets:
                        story.append(Paragraph(f"•  {b}", bullet_style))
                    story.append(Spacer(1, 1))

            elif sec == "skills" and resume.skill_categories:
                story.append(Paragraph("<b>TECHNICAL SKILLS</b>", sec_title_style))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=1, spaceAfter=3))
                for cat in resume.skill_categories:
                    line = f"<b>{cat.category_name}:</b> {' • '.join(cat.skills)}"
                    story.append(Paragraph(line, skill_style))

        doc.build(story)
        return pdf_path
