from __future__ import annotations
"""Extract recruiter email address from a block of text."""
import re

def extract_email(text: str) -> str | None:
    """Return the 'best' email address found in *text*, prioritizing personal over generic."""
    # Pattern includes a lookbehind/lookahead equivalent to avoid matching trailing dots
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text)
    if not matches:
        return None
        
    # Standardize and deduplicate
    matches_clean = []
    seen = set()
    for m in matches:
        # Sometimes regex captures trailing periods or punctuation like 'email.com.'
        cleaned = m.rstrip(".,;:)'\"]").lower()
        if cleaned not in seen:
            seen.add(cleaned)
            matches_clean.append(cleaned)
            
    # Generic prefixes to avoid if a personalized one is available
    generic_prefixes = {"hr", "info", "careers", "jobs", "support", "contact", "apply", "talent", "hello", "admin"}
    
    personal_matches = []
    generic_matches = []
    
    for match in matches_clean:
        prefix = match.split("@")[0]
        if any(g in prefix for g in generic_prefixes):
            generic_matches.append(match)
        else:
            personal_matches.append(match)
            
    # Prefer a personal match over a generic one
    if personal_matches:
        return personal_matches[0]
    return generic_matches[0]
