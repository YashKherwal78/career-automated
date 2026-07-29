import html as html_lib
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """Converts an HTML fragment (e.g. a job description body) to plain text."""
    if not text:
        return ""
    cleaned = _TAG_RE.sub(" ", text)
    cleaned = html_lib.unescape(cleaned)
    return _WS_RE.sub(" ", cleaned).strip()
