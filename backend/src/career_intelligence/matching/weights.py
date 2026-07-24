from typing import Dict

# Configurable defaults representing user-adjusted weighting settings
DEFAULT_MATCH_WEIGHTS: Dict[str, float] = {
    "skills": 0.20,
    "technologies": 0.25,
    "experience": 0.20,
    "projects": 0.10,
    "education": 0.10,
    "location": 0.08,
    "employment": 0.04,
    "certifications": 0.03
}
