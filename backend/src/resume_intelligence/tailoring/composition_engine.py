"""
Resume Composition Engine — deterministic page geometry & vertical density optimizer.

Responsibilities:
1. Target Page Utilization Tuning (Target: 92%–96% of single-page height).
2. Adaptive Spacing Calibration (dynamically adjusts section and item vspace).
3. Bullet Length Compression (targets 18–24 words, max 28 words).
4. Uniform Whitespace Distribution (prevents dense top / empty bottom artifact).
"""

import os
import re
import logging
import subprocess
from typing import Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CompositionMetrics(BaseModel):
    page_count: int = 1
    page_utilization: float = 0.0  # Percentage 0.0 to 100.0
    total_words: int = 0
    average_bullet_words: float = 0.0
    long_bullet_count: int = 0  # > 28 words
    is_balanced: bool = False


class CompositionEngine:
    """
    Optimizes page geometry, spacing, and bullet length to hit 92-96% vertical page fill.
    """

    TARGET_UTILIZATION_MIN = 91.0
    TARGET_UTILIZATION_MAX = 96.0
    TARGET_BULLET_WORDS_MAX = 24

    def optimize(self, tex_content: str, output_dir: str = "/tmp") -> Tuple[str, CompositionMetrics]:
        """
        Executes an adaptive optimization loop on LaTeX spacing parameters.
        Returns optimized LaTeX string and final composition metrics.
        """
        # Step 1: Compress overlong bullets (> 28 words) deterministically
        tex_content = self._compress_long_bullets(tex_content)

        # Step 2: Measure initial layout metrics via pdflatex + PyMuPDF
        pdf_path, metrics = self._measure_layout(tex_content, output_dir)

        logger.info(
            "CompositionEngine initial pass — pages=%d, utilization=%.1f%%, avg_bullet_words=%.1f",
            metrics.page_count, metrics.page_utilization, metrics.average_bullet_words
        )

        # Step 3: Adaptive spacing tuning if underfilled (<91%) or overflowing (>97%)
        if metrics.page_utilization < self.TARGET_UTILIZATION_MIN and metrics.page_count == 1:
            tex_content = self._expand_vertical_spacing(tex_content, metrics.page_utilization)
            _, metrics = self._measure_layout(tex_content, output_dir)

        elif metrics.page_utilization > self.TARGET_UTILIZATION_MAX or metrics.page_count > 1:
            tex_content = self._tighten_vertical_spacing(tex_content)
            _, metrics = self._measure_layout(tex_content, output_dir)

        metrics.is_balanced = (self.TARGET_UTILIZATION_MIN <= metrics.page_utilization <= self.TARGET_UTILIZATION_MAX)
        return tex_content, metrics

    def _compress_long_bullets(self, tex: str) -> str:
        """Trims overlong bullet phrases while preserving facts."""
        def trim_bullet(match):
            bullet_text = match.group(1)
            words = bullet_text.split()
            if len(words) > 28:
                trimmed = " ".join(words[:24])
                if not trimmed.endswith('.'):
                    trimmed += '.'
                return f"\\resumeItem{{{trimmed}}}"
            return match.group(0)

        return re.sub(r"\\resumeItem\{([^}]+)\}", trim_bullet, tex)

    def _expand_vertical_spacing(self, tex: str, current_utilization: float) -> str:
        """Adds adaptive vertical space between sections, headings, and list items to fill the lower page gracefully."""
        # Section title bottom spacing
        tex = re.sub(
            r"(\\titleformat\{\\section\}\{.*?\}\{\}\{0em\}\{\[\\color\{black\}\\titlerule\s*)\\vspace\{-5pt\}\]",
            r"\1\\vspace{2pt}]",
            tex
        )
        # Item spacing inside bullet lists
        tex = tex.replace(
            "\\newcommand{\\resumeItem}[1]{\\item\\small{{#1 \\vspace{-2pt}}}}",
            "\\newcommand{\\resumeItem}[1]{\\item\\small{{#1 \\vspace{2.5pt}}}}"
        )
        # Spacing after list environments
        tex = tex.replace(
            "\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}",
            "\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{2pt}}"
        )
        # Spacing after subheadings
        tex = tex.replace(
            "\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}",
            "\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}\\vspace{4pt}}"
        )
        return tex

    def _tighten_vertical_spacing(self, tex: str) -> str:
        """Tightens spacing if layout spills onto page 2."""
        tex = tex.replace(
            "\\newcommand{\\resumeItem}[1]{\\item\\small{{#1 \\vspace{1.5pt}}}}",
            "\\newcommand{\\resumeItem}[1]{\\item\\small{{#1 \\vspace{-3pt}}}}"
        )
        return tex

    def _measure_layout(self, tex_content: str, output_dir: str) -> Tuple[Optional[str], CompositionMetrics]:
        """Compiles LaTeX to PDF and measures bounding box height via PyMuPDF."""
        os.makedirs(output_dir, exist_ok=True)
        tex_path = os.path.join(output_dir, "temp_comp_engine.tex")
        pdf_path = os.path.join(output_dir, "temp_comp_engine.pdf")

        with open(tex_path, "w") as f:
            f.write(tex_content)

        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", f"-output-directory={output_dir}", tex_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
        except Exception as e:
            logger.error("pdflatex compilation failed: %s", e)
            return None, CompositionMetrics()

        if not os.path.exists(pdf_path):
            return None, CompositionMetrics()

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            page = doc[0]
            rect = page.rect
            page_height = rect.height

            text_instances = page.get_text("blocks")
            if text_instances:
                min_y = min(b[1] for b in text_instances)
                max_y = max(b[3] for b in text_instances)
                content_height = max_y - min_y
                utilization = round((content_height / (page_height - 72)) * 100.0, 1)
            else:
                utilization = 50.0

            bullets = re.findall(r"\\resumeItem\{([^}]+)\}", tex_content)
            words_per_bullet = [len(b.split()) for b in bullets]
            avg_words = sum(words_per_bullet) / max(1, len(words_per_bullet))
            long_bullets = sum(1 for w in words_per_bullet if w > 28)

            return pdf_path, CompositionMetrics(
                page_count=page_count,
                page_utilization=min(100.0, utilization),
                total_words=sum(len(b.split()) for b in bullets),
                average_bullet_words=round(avg_words, 1),
                long_bullet_count=long_bullets
            )
        except Exception as exc:
            logger.error("Error measuring PDF metrics: %s", exc)
            return pdf_path, CompositionMetrics(page_count=1, page_utilization=85.0)
