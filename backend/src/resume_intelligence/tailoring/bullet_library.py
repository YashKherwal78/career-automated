"""
Candidate Bullet Library & Role-Aware Dynamic Bullet Selector.

Exposes a rich multi-category bullet library per project and experience item.
Selects optimal role-specific bullets dynamically based on target Job Description requirements.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ProjectBulletLibrary(BaseModel):
    project_id: str
    title: str
    category_bullets: Dict[str, List[str]] = Field(default_factory=dict)
    # Categories e.g.: 'AI/Agents', 'Backend/Infra', 'Product/Metrics', 'Data/Analytics', 'Scaling'

    def get_bullets_for_role(self, role_type: str, limit: int = 2) -> List[str]:
        """Returns the top role-aligned candidate bullets."""
        r_type = role_type.upper()
        selected = []

        if r_type == "AI" and "AI/Agents" in self.category_bullets:
            selected.extend(self.category_bullets["AI/Agents"])
        elif r_type == "PRODUCT" and "Product/Metrics" in self.category_bullets:
            selected.extend(self.category_bullets["Product/Metrics"])
        elif r_type == "DATA" and "Data/Analytics" in self.category_bullets:
            selected.extend(self.category_bullets["Data/Analytics"])
        elif "Backend/Infra" in self.category_bullets:
            selected.extend(self.category_bullets["Backend/Infra"])

        # Fallback to general pool if category specific count is insufficient
        for cats in self.category_bullets.values():
            for b in cats:
                if b not in selected:
                    selected.append(b)

        return selected[:limit]


# Master Bullet Library Registry for Knowledge Projects
CAREER_AUTOMATED_BULLET_LIBRARY = ProjectBulletLibrary(
    project_id="proj_career_automated",
    title="CareerAutomated",
    category_bullets={
        "AI/Agents": [
            "Designed a Generator-Critic architecture: specialised agents handle company intelligence, project selection, and email generation; Critic agent validates formatting and placeholder safety.",
            "Building an autonomous AI recruiting platform orchestrating job discovery, candidate-job matching, resume tailoring, and inbox intelligence via LangGraph."
        ],
        "Backend/Infra": [
            "Engineered scalable data pipelines using SQLite, Pandas, IMAP, and SMTP to maintain recruiter state and deduplicate 10,000+ contacts.",
            "Built Playwright-based browser automation to execute ATS-specific application submission flows end-to-end with retry handling."
        ],
        "Product/Metrics": [
            "Defined system-wide quality gates blocking unsafe recruiter outreach, reducing manual application review time by 80%.",
            "Scoped 0-to-1 recruiter CRM workflow tracking email delivery, open rates, and candidate pipeline transitions in real time."
        ]
    }
)
