import os
import subprocess
from typing import Dict, Any

class ResumeCompiler:
    def compile(self, knowledge: Dict[str, Any], template_path: str, output_dir: str):
        # We will dynamically replace bullets in the base tex file for this proof of concept
        with open(template_path, 'r') as f:
            tex = f.read()
            
        projects = knowledge.get('projects', [])
        # For POC, replace project 1 bullet 1
        # In a full system we'd use Jinja2 for latex
        if projects and len(projects[0]['bullets']) > 0:
            new_bullet = projects[0]['bullets'][0].replace('%', '\\%').replace('&', '\\&')
            # Look for the old bullet
            old_bullet = "Building an \\kw{autonomous AI recruiting platform}"
            if old_bullet in tex:
                tex = tex.replace(old_bullet, new_bullet)
                
        out_tex = os.path.join(output_dir, "tailored_resume.tex")
        with open(out_tex, 'w') as f:
            f.write(tex)
            
        # Compile
        subprocess.run(["pdflatex", "-output-directory", output_dir, out_tex], check=True, capture_output=True)
        return os.path.join(output_dir, "tailored_resume.pdf")
