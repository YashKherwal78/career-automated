"""
Jake Resume Compiler V1 Master Orchestrator.

Consumes a StructuredResume object and renders PDF, DOCX, and HTML outputs.
Zero AI reasoning — pure presentation rendering.
"""

import os
from typing import Dict, Any
from src.resume_intelligence.compiler.jake_resume.models import StructuredResume
from src.resume_intelligence.compiler.jake_resume.html_renderer import JakeHTMLRenderer
from src.resume_intelligence.compiler.jake_resume.pdf_renderer import JakePDFRenderer
from src.resume_intelligence.compiler.jake_resume.docx_renderer import JakeDOCXRenderer


from src.resume_intelligence.compiler.jake_resume.optimizer import PageOptimizer, OptimizationReport


class JakeResumeCompiler:
    """Master Compiler for Jake Resume V1 Layout with One-Page Optimization."""

    def __init__(self):
        self.html_renderer = JakeHTMLRenderer()
        self.pdf_renderer = JakePDFRenderer()
        self.docx_renderer = JakeDOCXRenderer()
        self.optimizer = PageOptimizer()

    def compile(
        self,
        structured_resume: StructuredResume,
        output_dir: str,
        filename_prefix: str = "jake_tailored_resume"
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        paths = {}

        # Define iterative PDF measurement closure
        def pdf_measurer(res: StructuredResume) -> int:
            pdf_path = os.path.join(output_dir, f"{filename_prefix}.pdf")
            tex_path = os.path.join(output_dir, f"{filename_prefix}.tex")
            self.pdf_renderer.render(res, pdf_path=pdf_path, tex_path=tex_path)
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                return len(reader.pages)
            except Exception:
                return 1

        # 0. Iterative Render-Measure-Optimize Pass
        opt_resume, opt_report = self.optimizer.optimize_iterative(structured_resume, pdf_measurer)

        # 1. HTML Render
        html_content = self.html_renderer.render(opt_resume)
        html_path = os.path.join(output_dir, f"{filename_prefix}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        paths["html"] = html_path

        # 2. PDF Render
        pdf_path = os.path.join(output_dir, f"{filename_prefix}.pdf")
        tex_path = os.path.join(output_dir, f"{filename_prefix}.tex")
        paths["pdf"] = self.pdf_renderer.render(opt_resume, pdf_path=pdf_path, tex_path=tex_path)
        paths["tex"] = tex_path

        # 3. DOCX Render
        docx_path = os.path.join(output_dir, f"{filename_prefix}.docx")
        paths["docx"] = self.docx_renderer.render(opt_resume, docx_path=docx_path)

        paths["optimization_report"] = opt_report.model_dump()
        return paths
