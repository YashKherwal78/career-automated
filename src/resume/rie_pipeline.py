import json
import yaml
import os
from typing import List, Dict, Any
from src.resume.models import StructuredJob, CandidateFit, RewriteStrategy, EditOperation

class RewritePlanner:
    def generate_strategy(self, job: StructuredJob, fit: CandidateFit) -> RewriteStrategy:
        # Deterministic strategy generation
        return RewriteStrategy(
            priority_skills=job.mandatory_skills[:3],
            priority_responsibilities=job.responsibilities[:2],
            tone="Assertive",
            sections_to_prioritize=["proj_1", "exp_1"],
            bullet_order={},
            rewrite_style="assertive"
        )

class ResumeEditor:
    def generate_operations(self, strategy: RewriteStrategy, knowledge: Dict[str, Any]) -> List[EditOperation]:
        # Simulated LLM output
        ops = []
        ops.append(EditOperation(
            action="rewrite",
            project_id="proj_1",
            bullet_index=0,
            new_text="Built an autonomous AI recruiting platform using Python and LangGraph, optimizing job discovery and matching.",
            from_index=None,
            to_index=None,
            reason="Matched priority skills"
        ))
        return ops
        
    def apply_operations(self, knowledge: Dict[str, Any], ops: List[EditOperation]) -> Dict[str, Any]:
        import copy
        new_k = copy.deepcopy(knowledge)
        for op in ops:
            if op.action == "rewrite":
                # find in projects
                for p in new_k.get('projects', []):
                    if p['id'] == op.project_id:
                        p['bullets'][op.bullet_index] = op.new_text
        return new_k

class SemanticValidator:
    def validate(self, original: Dict, updated: Dict, ops: List[EditOperation]) -> bool:
        # Check for hallucinations
        for op in ops:
            if op.new_text and "AWS" in op.new_text and "AWS" not in str(original):
                return False
        return True

class StructuralValidator:
    def validate(self, knowledge: Dict) -> bool:
        # Check counts
        if not knowledge.get('projects'):
            return False
        return True

class ResumeCompiler:
    def compile(self, knowledge: Dict, output_path: str):
        # Generate LaTeX and compile to PDF (Mock)
        tex_content = r"\documentclass{article}\begin{document}Mock PDF\end{document}"
        with open("scratch/mock.tex", "w") as f:
            f.write(tex_content)
        # In a real scenario, pdflatex is called here
        with open(output_path, "w") as f:
            f.write("PDF BINARY MOCK")
        return True

class RIEPipeline:
    def run(self, job: StructuredJob, fit: CandidateFit):
        # 1. Load Knowledge
        with open("data/resume_knowledge/projects.yaml") as f:
            projects = yaml.safe_load(f)
        knowledge = {"projects": projects}
        
        # 2. Plan
        planner = RewritePlanner()
        strategy = planner.generate_strategy(job, fit)
        
        with open("scratch/RewriteStrategy.json", "w") as f:
            json.dump(strategy.__dict__, f, indent=2)
            
        # 3. Edit
        editor = ResumeEditor()
        ops = editor.generate_operations(strategy, knowledge)
        
        with open("scratch/EditOperations.json", "w") as f:
            json.dump([op.__dict__ for op in ops], f, indent=2)
            
        updated_knowledge = editor.apply_operations(knowledge, ops)
        
        # 4. Validate
        sem_val = SemanticValidator()
        if not sem_val.validate(knowledge, updated_knowledge, ops):
            raise Exception("Semantic Validation Failed")
            
        struc_val = StructuralValidator()
        if not struc_val.validate(updated_knowledge):
            raise Exception("Structural Validation Failed")
            
        # 5. Compile
        compiler = ResumeCompiler()
        compiler.compile(updated_knowledge, "scratch/TailoredResume.pdf")
        
        print("RIE Pipeline Completed Successfully!")

if __name__ == "__main__":
    job = StructuredJob("1", "OpenAI", "AI Engineer", "...", 2, 5, ["Python"], [], ["Build AI"], "AI", 0.99)
    fit = CandidateFit(True, [], ["Python"], False, None)
    pipe = RIEPipeline()
    pipe.run(job, fit)
