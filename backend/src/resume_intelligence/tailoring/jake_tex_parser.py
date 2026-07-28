"""
Jake Template Parser — deterministic structural parser for the Jake resume .tex format.

We control the compiler, so we know exactly what the LaTeX looks like.
This parser does NOT use a general LaTeX parser or regex-only heuristics.
It understands the precise Jake template structure and walks the file
character-by-character using a brace-depth counter to safely extract
\resumeItem{...} content even when bullets span multiple lines.

Parse tree:
    ParsedResumeTree
      ├── contact_block: str          (LOCKED, never rewritten)
      ├── summary_block: Optional[str] (rewritable content only)
      ├── sections: List[ParsedSection]
      │     └── ParsedSection
      │           ├── name: str
      │           └── entries: List[ParsedEntry]
      │                 └── ParsedEntry
      │                       ├── entry_type: "experience" | "project"
      │                       ├── heading_tokens: List[str]
      │                       └── bullets: List[ParsedBullet]
      │                             └── ParsedBullet
      │                                   ├── raw_content: str
      │                                   ├── char_start: int
      │                                   └── char_end: int
      └── skills_block: str            (LOCKED, never rewritten)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Parse tree nodes
# ---------------------------------------------------------------------------

@dataclass
class ParsedBullet:
    """Content inside one \\resumeItem{...} with exact character offsets into the original .tex."""
    raw_content: str
    """Everything between the outermost braces of \\resumeItem{...}."""
    char_start: int
    """Character index of the opening '{' (exclusive — first char of content)."""
    char_end: int
    """Character index of the matching closing '}' (exclusive — last char of content)."""


@dataclass
class ParsedEntry:
    """One \\resumeSubheading (experience) or \\resumeProjectHeading (project) block."""
    entry_type: str
    """'experience' or 'project'"""
    heading_tokens: List[str] = field(default_factory=list)
    """
    For experience: [company, date, title, location] (4 brace args).
    For project:    [title_and_tech, date] (2 brace args).
    """
    bullets: List[ParsedBullet] = field(default_factory=list)


@dataclass
class ParsedSection:
    name: str
    """Section name exactly as it appears in \\section{NAME}."""
    entries: List[ParsedEntry] = field(default_factory=list)


@dataclass
class ParsedResumeTree:
    """
    Complete parse tree of a Jake-format resume.
    contact_block and skills_block are raw .tex strings that are LOCKED.
    """
    contact_block: str = ""
    summary_block: Optional[str] = None
    """
    If a \\section{Summary} exists, this holds its text content.
    Otherwise None (engine will add no summary — forbidden operation).
    """
    summary_char_start: int = -1
    """Character offset of the summary content start in original .tex (or -1 if absent)."""
    summary_char_end: int = -1
    sections: List[ParsedSection] = field(default_factory=list)
    skills_block: str = ""


# ---------------------------------------------------------------------------
# Brace extractor helper
# ---------------------------------------------------------------------------

def _extract_brace_content(tex: str, open_pos: int) -> Tuple[str, int]:
    """
    Given the position of a '{' in `tex`, return (content, end_pos)
    where content is everything inside the matching '}'.
    end_pos is the index of the matching '}'.

    Handles nested braces correctly via a depth counter.
    Raises ValueError if braces are unmatched.
    """
    if tex[open_pos] != "{":
        raise ValueError(f"Expected '{{' at position {open_pos}, got '{tex[open_pos]}'")

    depth = 0
    i = open_pos
    content_start = open_pos + 1

    while i < len(tex):
        ch = tex[i]
        if ch == "\\" and i + 1 < len(tex):
            # Skip escaped character — don't count it as a brace
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return tex[content_start:i], i
        i += 1

    raise ValueError(
        f"Unmatched brace starting at position {open_pos} in resume .tex"
    )


def _extract_n_brace_args(tex: str, start: int, n: int) -> Tuple[List[str], int]:
    """
    Extract `n` consecutive brace-enclosed arguments from `tex` starting at `start`.
    Returns (list_of_contents, position_after_last_closing_brace).
    Skips whitespace and newlines between arguments.
    """
    args: List[str] = []
    pos = start
    for _ in range(n):
        # Skip whitespace between args
        while pos < len(tex) and tex[pos] in " \t\n\r":
            pos += 1
        if pos >= len(tex) or tex[pos] != "{":
            break
        content, end_pos = _extract_brace_content(tex, pos)
        args.append(content)
        pos = end_pos + 1  # move past closing '}'
    return args, pos


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

# Jake template section names we understand
_LOCKED_SECTIONS = {"Technical Skills", "Skills"}
_REWRITABLE_SECTIONS = {"Experience", "Projects"}
_SUMMARY_SECTIONS = {"Summary", "Profile", "Objective"}

# LaTeX command tokens we look for (without backslash)
_CMD_SECTION = "\\section{"
_CMD_SUBHEADING = "\\resumeSubheading"
_CMD_PROJECT_HEADING = "\\resumeProjectHeading"
_CMD_ITEM = "\\resumeItem{"
_CONTACT_START = "\\begin{center}"
_CONTACT_END = "\\end{center}"
_DOC_BEGIN = "\\begin{document}"


class JakeTexParser:
    """
    Deterministic parser for the Jake LaTeX resume template.

    Works character-indexed — never modifies the input string.
    All char_start / char_end offsets in ParsedBullet refer to positions
    in the original .tex string passed to parse().
    """

    def parse(self, tex: str) -> ParsedResumeTree:
        tree = ParsedResumeTree()

        # ── 1. Locate \begin{document} ─────────────────────────────────────
        doc_pos = tex.find(_DOC_BEGIN)
        if doc_pos == -1:
            doc_pos = 0  # fallback: treat whole file as document body

        body = tex  # we keep offsets into the full tex string

        # ── 2. Extract contact block ───────────────────────────────────────
        center_start = tex.find(_CONTACT_START, doc_pos)
        center_end = tex.find(_CONTACT_END, center_start if center_start != -1 else doc_pos)
        if center_start != -1 and center_end != -1:
            tree.contact_block = tex[center_start : center_end + len(_CONTACT_END)]

        # ── 3. Walk sections ───────────────────────────────────────────────
        search_from = center_end + len(_CONTACT_END) if center_end != -1 else doc_pos

        while True:
            sec_pos = tex.find(_CMD_SECTION, search_from)
            if sec_pos == -1:
                break

            # Extract section name
            name_content, name_end = _extract_brace_content(tex, sec_pos + len("\\section"))
            name = name_content.strip()
            after_section_header = name_end + 1

            # Find where the next section starts (or end of document)
            next_sec_pos = tex.find(_CMD_SECTION, after_section_header)
            end_doc_pos = tex.find("\\end{document}", after_section_header)
            section_end = min(
                x for x in [next_sec_pos, end_doc_pos, len(tex)] if x != -1
            )
            section_body = tex[after_section_header:section_end]
            section_body_offset = after_section_header  # offset to translate indices

            if name in _LOCKED_SECTIONS:
                tree.skills_block = tex[sec_pos:section_end]
                search_from = section_end
                continue

            if name in _SUMMARY_SECTIONS:
                # Extract plain text content of the summary section
                summary_content, s_start, s_end = self._extract_summary(
                    tex, after_section_header, section_end
                )
                tree.summary_block = summary_content
                tree.summary_char_start = s_start
                tree.summary_char_end = s_end
                search_from = section_end
                continue

            if name in _REWRITABLE_SECTIONS:
                parsed_sec = self._parse_section(
                    name, tex, after_section_header, section_end
                )
                tree.sections.append(parsed_sec)
                search_from = section_end
            else:
                # Unknown section — skip, don't touch
                search_from = section_end

        return tree

    # ── Section body parser ────────────────────────────────────────────────

    def _parse_section(
        self, name: str, tex: str, start: int, end: int
    ) -> ParsedSection:
        section = ParsedSection(name=name)
        pos = start

        while pos < end:
            # Look for the next entry header
            sub_pos = tex.find("\\resumeSubheading", pos)
            proj_pos = tex.find("\\resumeProjectHeading", pos)

            # Pick whichever comes first within this section
            candidates = [(p, t) for p, t in [(sub_pos, "experience"), (proj_pos, "project")] if p != -1 and p < end]
            if not candidates:
                break

            entry_pos, entry_type = min(candidates, key=lambda x: x[0])

            # Extract heading tokens
            cmd_len = len("\\resumeSubheading") if entry_type == "experience" else len("\\resumeProjectHeading")
            n_args = 4 if entry_type == "experience" else 2
            heading_tokens, after_heading = _extract_n_brace_args(
                tex, entry_pos + cmd_len, n_args
            )

            # Find the end of this entry (next heading or section end)
            next_sub = tex.find("\\resumeSubheading", after_heading)
            next_proj = tex.find("\\resumeProjectHeading", after_heading)
            entry_end_candidates = [
                x for x in [next_sub, next_proj, end] if x != -1 and x > after_heading
            ]
            entry_end = min(entry_end_candidates)

            # Extract all \resumeItem{} bullets within this entry
            bullets = self._extract_bullets(tex, after_heading, entry_end)

            entry = ParsedEntry(
                entry_type=entry_type,
                heading_tokens=heading_tokens,
                bullets=bullets,
            )
            section.entries.append(entry)
            pos = entry_end

        return section

    # ── Bullet extractor ───────────────────────────────────────────────────

    def _extract_bullets(self, tex: str, start: int, end: int) -> List[ParsedBullet]:
        bullets: List[ParsedBullet] = []
        pos = start

        while pos < end:
            item_pos = tex.find(_CMD_ITEM, pos)
            if item_pos == -1 or item_pos >= end:
                break

            # The '{' is part of _CMD_ITEM — it's already included
            open_brace_pos = item_pos + len(_CMD_ITEM) - 1  # position of '{'
            content, close_pos = _extract_brace_content(tex, open_brace_pos)
            bullets.append(ParsedBullet(
                raw_content=content,
                char_start=open_brace_pos + 1,  # first char of content
                char_end=close_pos,             # closing '}'
            ))
            pos = close_pos + 1

        return bullets

    # ── Summary extractor ──────────────────────────────────────────────────

    def _extract_summary(
        self, tex: str, start: int, end: int
    ) -> Tuple[str, int, int]:
        """
        Extracts summary text content from the section body.
        Returns (content, char_start, char_end) or ('', -1, -1) if not found.
        Jake summaries are typically inside a \resumeItem or plain paragraph text.
        """
        # Look for a \resumeItem in the summary section first
        item_pos = tex.find(_CMD_ITEM, start)
        if item_pos != -1 and item_pos < end:
            open_brace_pos = item_pos + len(_CMD_ITEM) - 1
            content, close_pos = _extract_brace_content(tex, open_brace_pos)
            return content, open_brace_pos + 1, close_pos

        # Fallback: extract plain text between section header and next section
        raw = tex[start:end].strip()
        # Remove LaTeX command lines
        lines = [ln for ln in raw.split("\n") if not ln.strip().startswith("\\")]
        content = " ".join(lines).strip()
        if content:
            idx = tex.find(content, start)
            if idx != -1 and idx < end:
                return content, idx, idx + len(content)

        return "", -1, -1
