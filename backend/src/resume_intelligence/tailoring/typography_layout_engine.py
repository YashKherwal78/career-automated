"""
Typography & Layout Engine — multi-stage typography, scale, and optical presentation optimizer.

Hierarchy of Optimization:
Stage 1: Font Scaling (10.0pt → 10.8pt)
Stage 2: Line Spacing / Baselineskip (1.00 → 1.06)
Stage 3: Section Spacing (\vspace)
Stage 4: Bullet Item Spacing (\resumeItem \vspace)

HARD LIMITS:
- Margins: LOCKED (Never modified)
- Target Utilization: 92.0% - 96.0% (Hard Max: 98.0%)
"""

import os
import re
import logging
import subprocess
from typing import Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LayoutMetrics(BaseModel):
    page_count: int = 1
    page_utilization: float = 0.0  # 0.0 to 100.0%
    font_size_pt: float = 10.5
    line_stretch: float = 1.00
    section_space_pt: float = -4.0
    item_space_pt: float = -2.0
    section_proportions: dict = {}  # Section name -> % of content height
    is_optically_balanced: bool = False


class TypographyLayoutEngine:
    """
    Optimizes document presentation via typography scaling first, then line height, then spacing.
    Enforces strict hard limits and optical section balance.
    """

    TARGET_UTIL_MIN = 92.0
    TARGET_UTIL_MAX = 96.0
    HARD_UTIL_MAX = 98.0

    # Ideal visual proportions per section
    IDEAL_PROPORTIONS = {
        "Experience": (0.45, 0.60),
        "Projects": (0.12, 0.22),
        "Education": (0.07, 0.14),
        "Technical Skills": (0.08, 0.15),
    }

    def optimize(self, tex_content: str, output_dir: str = "/tmp") -> Tuple[str, LayoutMetrics]:
        """
        Executes 4-stage typography & layout optimization ladder with Optical Balance evaluation.
        """
        current_tex = tex_content
        output_pdf, metrics = self._measure_layout(current_tex, output_dir)

        logger.info(
            "TypographyLayoutEngine initial — util=%.1f%%, font=%.1fpt, pages=%d",
            metrics.page_utilization, metrics.font_size_pt, metrics.page_count
        )

        # Stage 1: Scale Font Size (10.0pt → 11.0pt)
        if metrics.page_utilization < self.TARGET_UTIL_MIN and metrics.page_count == 1:
            for font_pt in [10.5, 10.8, 11.0]:
                test_tex = self._set_font_size(current_tex, font_pt)
                test_pdf, test_metrics = self._measure_layout(test_tex, output_dir)
                if test_metrics.page_count == 1 and test_metrics.page_utilization <= self.HARD_UTIL_MAX:
                    current_tex, metrics = test_tex, test_metrics
                    if self.TARGET_UTIL_MIN <= metrics.page_utilization <= self.TARGET_UTIL_MAX:
                        break
                else:
                    break

        # Stage 2: Adjust Line Height / Stretch (1.00 → 1.06)
        if metrics.page_utilization < self.TARGET_UTIL_MIN and metrics.page_count == 1:
            for stretch in [1.02, 1.04, 1.06]:
                test_tex = self._set_line_stretch(current_tex, stretch)
                test_pdf, test_metrics = self._measure_layout(test_tex, output_dir)
                if test_metrics.page_count == 1 and test_metrics.page_utilization <= self.HARD_UTIL_MAX:
                    current_tex, metrics = test_tex, test_metrics
                    if self.TARGET_UTIL_MIN <= metrics.page_utilization <= self.TARGET_UTIL_MAX:
                        break
                else:
                    break

        # Stage 3: Fine-tune Section Spacing
        if metrics.page_utilization < self.TARGET_UTIL_MIN and metrics.page_count == 1:
            test_tex = self._set_section_spacing(current_tex, 1.0)
            test_pdf, test_metrics = self._measure_layout(test_tex, output_dir)
            if test_metrics.page_count == 1 and test_metrics.page_utilization <= self.HARD_UTIL_MAX:
                current_tex, metrics = test_tex, test_metrics

        # Stage 4: Fine-tune Bullet Item Spacing
        if metrics.page_utilization < self.TARGET_UTIL_MIN and metrics.page_count == 1:
            test_tex = self._set_item_spacing(current_tex, 1.5)
            test_pdf, test_metrics = self._measure_layout(test_tex, output_dir)
            if test_metrics.page_count == 1 and test_metrics.page_utilization <= self.HARD_UTIL_MAX:
                current_tex, metrics = test_tex, test_metrics

        # Evaluate Optical Section Balance
        metrics.is_optically_balanced = self._check_optical_balance(metrics)
        return current_tex, metrics

    def _check_optical_balance(self, metrics: LayoutMetrics) -> bool:
        """Verifies if section proportions fall within ideal optical bounds."""
        if not (self.TARGET_UTIL_MIN <= metrics.page_utilization <= self.HARD_UTIL_MAX):
            return False
        if not metrics.section_proportions:
            return True
        for sec, (min_p, max_p) in self.IDEAL_PROPORTIONS.items():
            prop = metrics.section_proportions.get(sec, 0.0)
            if prop > 0 and not (min_p * 0.8 <= prop <= max_p * 1.25):
                logger.info("Section '%s' out of optical proportion: %.2f", sec, prop)
                return False
        return True

    def _set_font_size(self, tex: str, size_pt: float) -> str:
        """Scales document body font size smoothly without altering margins."""
        baseline_pt = round(size_pt * 1.25, 1)
        font_cmd = f"\\\\fontsize{{{size_pt}pt}}{{{baseline_pt}pt}}\\\\selectfont"
        if "\\fontsize{" in tex:
            return re.sub(r"\\fontsize\{[\d\.]+pt\}\{[\d\.]+pt\}\\selectfont", font_cmd, tex)
        else:
            return tex.replace("\\begin{document}", f"\\begin{{document}}\n\\fontsize{{{size_pt}pt}}{{{baseline_pt}pt}}\\selectfont")

    def _set_line_stretch(self, tex: str, stretch: float) -> str:
        """Adjusts baseline line stretch."""
        if "\\linespread{" in tex:
            return re.sub(r"\\linespread\{[\d\.]+\}", f"\\\\linespread{{{stretch}}}", tex)
        else:
            return tex.replace("\\begin{document}", f"\\begin{{document}}\n\\linespread{{{stretch}}}")

    def _set_section_spacing(self, tex: str, space_pt: float) -> str:
        """Adjusts section bottom spacing."""
        return re.sub(
            r"(\\titleformat\{\\section\}\{.*?\}\{\}\{0em\}\{\[\\color\{black\}\\titlerule\s*)\\vspace\{[-?\d\.]+pt\}\]",
            f"\\\\1\\\\vspace{{{space_pt}pt}}]",
            tex
        )

    def _set_item_spacing(self, tex: str, space_pt: float) -> str:
        """Adjusts item vspace."""
        return tex.replace(
            "\\newcommand{\\resumeItem}[1]{\\item\\small{{#1 \\vspace{-2pt}}}}",
            f"\\newcommand{{\\resumeItem}}[1]{{\\item\\small{{#1 \\vspace{{{space_pt}pt}}}}}}"
        )

    def _measure_layout(self, tex_content: str, output_dir: str) -> Tuple[Optional[str], LayoutMetrics]:
        """Compiles LaTeX to PDF and measures bounding box height and section proportions via PyMuPDF."""
        os.makedirs(output_dir, exist_ok=True)
        tex_path = os.path.join(output_dir, "temp_typo_engine.tex")
        pdf_path = os.path.join(output_dir, "temp_typo_engine.pdf")

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
            logger.error("pdflatex compilation error: %s", e)
            return None, LayoutMetrics()

        if not os.path.exists(pdf_path):
            return None, LayoutMetrics()

        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            page = doc[0]
            rect = page.rect
            page_height = rect.height

            text_instances = page.get_text("blocks")
            section_props = {}
            if text_instances:
                min_y = min(b[1] for b in text_instances)
                max_y = max(b[3] for b in text_instances)
                content_height = max(1.0, max_y - min_y)
                utilization = round((content_height / (page_height - 72)) * 100.0, 1)

                # Estimate section proportions from text blocks
                for b in text_instances:
                    txt = b[4].strip()
                    block_h = b[3] - b[1]
                    for sec_name in ["Experience", "Projects", "Education", "Technical Skills"]:
                        if sec_name in txt:
                            section_props[sec_name] = round(block_h / content_height, 2)
            else:
                utilization = 50.0

            font_match = re.search(r"\\documentclass\[letterpaper,\s*([\d\.]+)pt\]", tex_content)
            font_size = float(font_match.group(1)) if font_match else 10.5

            stretch_match = re.search(r"\\linespread\{([\d\.]+)\}", tex_content)
            stretch = float(stretch_match.group(1)) if stretch_match else 1.00

            return pdf_path, LayoutMetrics(
                page_count=page_count,
                page_utilization=min(100.0, utilization),
                font_size_pt=font_size,
                line_stretch=stretch,
                section_proportions=section_props
            )
        except Exception as exc:
            logger.error("Error measuring layout: %s", exc)
            return pdf_path, LayoutMetrics()
