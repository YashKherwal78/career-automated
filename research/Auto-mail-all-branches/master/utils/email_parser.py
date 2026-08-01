"""Extract recruiter email address from a block of text."""
import re


def extract_email(text: str) -> str | None:
    """Return the first email address found in *text*, or None."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    return match.group(0) if match else None
