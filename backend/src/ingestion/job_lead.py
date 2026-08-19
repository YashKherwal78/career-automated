from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class JobLead:
    company: str
    role: str
    apply_link: str
    location: Optional[str]
    jd_excerpt: Optional[str]
    source: Literal["screenshot", "email"]
    source_ref: str

    def is_valid(self) -> bool:
        return bool(self.company and self.role and self.apply_link)
