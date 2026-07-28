"""
Jake Resume HTML Renderer — Visually Identical Responsive & Print Layout.

Recreates the exact visual design philosophy of Jake Resume using modern, semantic HTML5/CSS:
- Single-line compact header bar
- Tight vertical padding & compact line heights
- High-density inline skill bullet separators (•)
- Tight bullet list spacing
"""

from jinja2 import Template
from src.resume_intelligence.compiler.jake_resume.models import StructuredResume

JAKE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ resume.name }} — Software Engineering Resume</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #0f172a;
        background-color: #ffffff;
        line-height: 1.35;
        font-size: 10pt;
        padding: 0.4in;
        max-width: 8.5in;
        margin: 0 auto;
    }

    @media print {
        body {
            padding: 0;
            max-width: 100%;
        }
    }

    /* HEADER */
    .header {
        text-align: center;
        margin-bottom: 8pt;
    }

    .candidate-name {
        font-size: 18pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #0f172a;
        margin-bottom: 2pt;
    }

    .contact-bar {
        font-size: 9pt;
        color: #334155;
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 5pt;
    }

    .contact-bar a {
        color: #0f172a;
        text-decoration: none;
    }

    .contact-bar a:hover {
        text-decoration: underline;
    }

    .separator {
        color: #64748b;
    }

    /* SECTIONS */
    .section {
        margin-bottom: 8pt;
    }

    .section-title {
        font-size: 10.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #0f172a;
        border-bottom: 1px solid #0f172a;
        padding-bottom: 1pt;
        margin-bottom: 4pt;
    }

    /* ITEM HEADINGS */
    .item-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-size: 10pt;
    }

    .title-primary {
        font-weight: 700;
        color: #0f172a;
    }

    .title-secondary {
        font-style: italic;
        font-weight: 400;
        color: #334155;
        font-size: 9.5pt;
    }

    .date-location {
        font-size: 9pt;
        font-weight: 500;
        color: #0f172a;
        white-space: nowrap;
    }

    .tech-stack {
        font-style: italic;
        font-weight: 400;
        font-size: 9pt;
        color: #334155;
    }

    /* BULLETS */
    ul.bullet-list {
        list-style-type: disc;
        margin-top: 2pt;
        margin-bottom: 4pt;
        padding-left: 14pt;
    }

    ul.bullet-list li {
        font-size: 9pt;
        color: #1e293b;
        margin-bottom: 1.5pt;
        line-height: 1.3;
    }

    /* SKILLS CATEGORIES */
    .skills-container {
        margin-top: 2pt;
    }

    .skill-row {
        font-size: 9pt;
        margin-bottom: 2pt;
        line-height: 1.35;
    }

    .skill-category {
        font-weight: 700;
        color: #0f172a;
    }

    .skill-list {
        color: #1e293b;
    }

    .summary-text {
        font-size: 9pt;
        color: #1e293b;
        line-height: 1.35;
        margin-bottom: 4pt;
    }
</style>
</head>
<body>

    <!-- HEADER -->
    <div class="header">
        <h1 class="candidate-name">{{ resume.name }}</h1>
        <div class="contact-bar">
            {% if resume.contact.phone %}<span>{{ resume.contact.phone }}</span><span class="separator">|</span>{% endif %}
            {% if resume.contact.email %}<a href="mailto:{{ resume.contact.email }}">{{ resume.contact.email }}</a><span class="separator">|</span>{% endif %}
            {% if resume.contact.linkedin %}<a href="{{ resume.contact.linkedin }}" target="_blank">LinkedIn</a><span class="separator">|</span>{% endif %}
            {% if resume.contact.github %}<a href="{{ resume.contact.github }}" target="_blank">GitHub</a>{% endif %}
            {% if resume.contact.portfolio %}<span class="separator">|</span><a href="{{ resume.contact.portfolio }}" target="_blank">Portfolio</a>{% endif %}
        </div>
    </div>

    <!-- DYNAMIC SECTIONS RENDERED ACCORDING TO RECOMMENDATION ENGINE ORDER -->
    {% for sec in resume.section_order %}
        {% if sec == 'summary' and resume.summary %}
            <div class="section">
                <h2 class="section-title">Professional Summary</h2>
                <p class="summary-text">{{ resume.summary }}</p>
            </div>
        {% elif sec == 'education' and resume.education %}
            <div class="section">
                <h2 class="section-title">Education</h2>
                {% for edu in resume.education %}
                    <div class="item-header">
                        <div>
                            <span class="title-primary">{{ edu.institution }}</span>
                        </div>
                        <div class="date-location">{{ edu.start_date }} – {{ edu.end_date }}</div>
                    </div>
                    <div class="item-header" style="margin-bottom: 2pt;">
                        <span class="title-secondary">{{ edu.degree }} in {{ edu.field_of_study }}</span>
                        {% if edu.location %}<span class="title-secondary">{{ edu.location }}</span>{% endif %}
                    </div>
                {% endfor %}
            </div>
        {% elif sec == 'experience' and resume.experience %}
            <div class="section">
                <h2 class="section-title">Experience</h2>
                {% for exp in resume.experience %}
                    <div class="item-header">
                        <div>
                            <span class="title-primary">{{ exp.title }}</span>
                        </div>
                        <div class="date-location">{{ exp.start_date }} – {{ exp.end_date }}</div>
                    </div>
                    <div class="item-header">
                        <span class="title-secondary">{{ exp.company }}</span>
                        {% if exp.location %}<span class="title-secondary">{{ exp.location }}</span>{% endif %}
                    </div>
                    {% if exp.bullets %}
                        <ul class="bullet-list">
                            {% for b in exp.bullets %}
                                <li>{{ b }}</li>
                            {% endfor %}
                        </ul>
                    {% endif %}
                {% endfor %}
            </div>
        {% elif sec == 'projects' and resume.projects %}
            <div class="section">
                <h2 class="section-title">Projects</h2>
                {% for proj in resume.projects %}
                    <div class="item-header">
                        <div>
                            <span class="title-primary">{{ proj.title }}</span>
                            {% if proj.technologies %}
                                <span class="tech-stack">| {{ proj.technologies | join(' • ') }}</span>
                            {% endif %}
                        </div>
                        <div class="date-location">{{ proj.date }}</div>
                    </div>
                    {% if proj.bullets %}
                        <ul class="bullet-list">
                            {% for b in proj.bullets %}
                                <li>{{ b }}</li>
                            {% endfor %}
                        </ul>
                    {% endif %}
                {% endfor %}
            </div>
        {% elif sec == 'skills' and resume.skill_categories %}
            <div class="section">
                <h2 class="section-title">Technical Skills</h2>
                <div class="skills-container">
                    {% for cat in resume.skill_categories %}
                        <div class="skill-row">
                            <span class="skill-category">{{ cat.category_name }}:</span>
                            <span class="skill-list">{{ cat.skills | join(' • ') }}</span>
                        </div>
                    {% endfor %}
                </div>
            </div>
        {% endif %}
    {% endfor %}

</body>
</html>
"""


class JakeHTMLRenderer:
    """HTML Renderer for Jake Resume V1."""

    def render(self, resume: StructuredResume) -> str:
        template = Template(JAKE_HTML_TEMPLATE)
        return template.render(resume=resume)
