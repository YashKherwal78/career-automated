"""
Macro Guard — placeholder substitution and restoration for LaTeX macros.

The LLM never sees raw LaTeX commands. Before the LLM call, all macros
(``\\kw{}``, ``\\textbf{}``, ``\\href{}{}``, ``\\emph{}``, ``\\small{}``) are replaced with
deterministic placeholders (__MACRO_1__, __MACRO_2__, ...).
After the LLM returns its patch ops, placeholders are restored exactly.

Design: JakeTexParser owns the document model (change #7).
MacroGuard operates only on strings extracted from that model — it never
parses the .tex directly.

Invariants:
  - Every placeholder in masked text MUST exist in PlaceholderMap.
  - Restoration is exact: if the LLM drops a placeholder, raise MacroRestoreError.
  - Placeholder keys are globally unique within a single tailor() session.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from src.resume_intelligence.tailoring.models_v1 import PlaceholderMap


# ---------------------------------------------------------------------------
# Regex patterns for known Jake-template macros (order matters — longest first)
# ---------------------------------------------------------------------------

# \href{url}{display text}  — two brace groups
_HREF_PATTERN = re.compile(r"\\href\{[^}]*\}\{[^}]*\}")

# \kw{content}  — bold keyword macro (Jake-specific)
_KW_PATTERN = re.compile(r"\\kw\{[^}]*\}")

# \textbf{content}
_TEXTBF_PATTERN = re.compile(r"\\textbf\{[^}]*\}")

# \emph{content}
_EMPH_PATTERN = re.compile(r"\\emph\{[^}]*\}")

# \small{content}
_SMALL_PATTERN = re.compile(r"\\small\{[^}]*\}")

# \textit{content}
_TEXTIT_PATTERN = re.compile(r"\\textit\{[^}]*\}")

# \rightarrow and similar single-token math/arrow macros
_ARROW_PATTERN = re.compile(r"\\(?:rightarrow|leftarrow|Rightarrow|Leftarrow|sim|approx)")

# Ordered list: patterns applied in this sequence to avoid partial matches
_MACRO_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("HREF",   _HREF_PATTERN),
    ("KW",     _KW_PATTERN),
    ("BOLD",   _TEXTBF_PATTERN),
    ("EMPH",   _EMPH_PATTERN),
    ("SMALL",  _SMALL_PATTERN),
    ("ITALIC", _TEXTIT_PATTERN),
    ("ARROW",  _ARROW_PATTERN),
]


class MacroRestoreError(ValueError):
    """Raised when a placeholder appears in LLM output but is missing from PlaceholderMap."""
    pass


class MacroGuard:
    """
    Stateless utility class.
    All state lives in the PlaceholderMap returned by mask().
    """

    @staticmethod
    def mask(text: str, counter_start: int = 1) -> Tuple[str, PlaceholderMap, int]:
        """
        Replace all LaTeX macros in `text` with deterministic placeholders.

        Args:
            text: Raw bullet/summary content (extracted from \\resumeItem{...}).
            counter_start: Starting integer for placeholder numbering.
                           Pass the running counter across multiple calls to
                           guarantee globally unique placeholders in a session.

        Returns:
            (masked_text, PlaceholderMap, next_counter)
        """
        pmap = PlaceholderMap()
        masked = text
        counter = counter_start

        for label, pattern in _MACRO_PATTERNS:
            def _replace(m: re.Match, _label: str = label, _c: list = [counter]) -> str:  # noqa: B023
                original = m.group(0)
                placeholder = f"__{_label}_{_c[0]}__"
                _c[0] += 1
                pmap.to_placeholder[original] = placeholder
                pmap.from_placeholder[placeholder] = original
                return placeholder

            # Reset inner counter for each pattern group
            _inner_counter = [counter]

            def _replace_with_shared(m: re.Match) -> str:  # noqa: ANN001
                original = m.group(0)
                if original in pmap.to_placeholder:
                    return pmap.to_placeholder[original]
                nonlocal counter
                placeholder = f"__{label}_{counter}__"
                pmap.to_placeholder[original] = placeholder
                pmap.from_placeholder[placeholder] = original
                counter += 1
                return placeholder

            masked = pattern.sub(_replace_with_shared, masked)

        return masked, pmap, counter

    @staticmethod
    def mask_bullets(
        bullets: List[str], counter_start: int = 1
    ) -> Tuple[List[str], PlaceholderMap, int]:
        """
        Mask all bullets in a list with a shared, globally unique counter.
        Returns (masked_bullets, combined_PlaceholderMap, next_counter).
        """
        combined = PlaceholderMap()
        masked_list: List[str] = []
        counter = counter_start

        for bullet in bullets:
            masked, pmap, counter = MacroGuard.mask(bullet, counter)
            masked_list.append(masked)
            combined.to_placeholder.update(pmap.to_placeholder)
            combined.from_placeholder.update(pmap.from_placeholder)

        return masked_list, combined, counter

    @staticmethod
    def restore(masked_text: str, pmap: PlaceholderMap) -> str:
        """
        Restore all placeholders in `masked_text` back to their original LaTeX macros.

        Raises MacroRestoreError if any placeholder in the text is missing from pmap.
        """
        result = masked_text
        # Find all placeholders still present
        remaining = re.findall(r"__[A-Z]+_\d+__", result)

        for ph in remaining:
            if ph not in pmap.from_placeholder:
                raise MacroRestoreError(
                    f"Placeholder '{ph}' in LLM output has no mapping in PlaceholderMap. "
                    "This means the LLM may have invented a placeholder or the session state is corrupt."
                )
            result = result.replace(ph, pmap.from_placeholder[ph])

        return result

    @staticmethod
    def restore_all(masked_texts: List[str], pmap: PlaceholderMap) -> List[str]:
        """Restore placeholders in a list of texts. Raises MacroRestoreError on any failure."""
        return [MacroGuard.restore(t, pmap) for t in masked_texts]

    @staticmethod
    def has_unrestored_placeholders(text: str) -> bool:
        """Return True if any __MACRO_N__ placeholders remain in text."""
        return bool(re.search(r"__[A-Z]+_\d+__", text))
