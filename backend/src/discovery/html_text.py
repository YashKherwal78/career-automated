import re

from bs4 import BeautifulSoup

_BLANK_RUN_RE = re.compile(r"[ \t]+")
_NEWLINE_RUN_RE = re.compile(r"\n{3,}")

# Tags whose CONTENT must be dropped entirely, not just the tag markers --
# confirmed real (2026-08-25): the previous regex-based stripper
# (`<[^>]+>` -> " ") only removed tag delimiters, leaving a <script>
# block's actual JS/CSS source sitting in the "plain text" description as
# if it were job-posting prose (embedding text, BM25 search_vector, and
# the dashboard's rendered description all inherited this).
_DROP_CONTENT_TAGS = ["script", "style", "noscript"]

# Only these introduce a line break -- confirmed real (2026-08-25):
# get_text(separator="\n") applies its separator at EVERY tag boundary,
# inline ones included, so "a <b>Software Engineer</b>." fragmented into
# "a\nSoftware Engineer\n." instead of reading as one sentence. Appending
# an explicit "\n" only after block-level tags (and swapping <br> for a
# literal newline) keeps paragraphs/list items on their own lines while
# leaving inline emphasis (<b>, <i>, <span>, <a>, <strong>) flowing
# in-line with the surrounding text, same as a browser would render it.
_BLOCK_TAGS = [
    "p", "div", "li", "tr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "table", "blockquote", "section", "article",
]


def strip_html(text: str) -> str:
    """Converts an HTML fragment (e.g. a job description body) to plain text.

    Uses BeautifulSoup+lxml (both already dependencies) rather than a
    regex tag-stripper -- a real parser handles malformed/nested markup,
    entity decoding, and <script>/<style> content removal correctly, none
    of which a `<[^>]+>` regex can do reliably. Preserves block-level
    structure (paragraphs, list items) as line breaks instead of
    collapsing an entire JD into one run-on sentence, which both reads
    better on the dashboard and gives BM25/embeddings a little more
    structure to work with.
    """
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    for tag in soup(_DROP_CONTENT_TAGS):
        tag.decompose()
    for tag in soup.find_all("br"):
        tag.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.append("\n")
    cleaned = soup.get_text()
    cleaned = _BLANK_RUN_RE.sub(" ", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.split("\n"))
    cleaned = _NEWLINE_RUN_RE.sub("\n\n", cleaned)
    return cleaned.strip()
