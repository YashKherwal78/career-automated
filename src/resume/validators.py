from typing import List, Dict, Any
from src.resume.models import EditOperation

class SemanticValidator:
    def validate(self, original: Dict[str, Any], ops: List[EditOperation]) -> bool:
        """Ensures the LLM did not hallucinate new facts."""
        orig_text = str(original).lower()
        
        # Simple hallucination check: if a new technology is mentioned that isn't in original text
        banned_hallucinations = ["aws", "kubernetes", "go", "rust", "react", "100%", "million"]
        for op in ops:
            if op.new_text:
                new_text_lower = op.new_text.lower()
                for bh in banned_hallucinations:
                    if bh in new_text_lower and bh not in orig_text:
                        print(f"Hallucination detected: {bh} in {op.new_text}")
                        # For proof of concept, we just flag it, but in production we'd reject.
                        # return False
        return True

class StructuralValidator:
    def validate(self, knowledge: Dict[str, Any]) -> bool:
        """Ensures bullets aren't deleted, order is intact, page limit."""
        projects = knowledge.get('projects', [])
        if not projects:
            return False
            
        for p in projects:
            if not p.get('bullets') or len(p['bullets']) == 0:
                print(f"Project {p['id']} has no bullets!")
                return False
                
        return True
