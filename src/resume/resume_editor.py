import json
from typing import List, Dict, Any
from src.resume.models import RewriteStrategy, EditOperation
from src.utils.llm_router import LLMRouter

class ResumeEditor:
    def __init__(self):
        self.router = LLMRouter()
        self.max_bullets = 8

    def generate_operations(self, strategy: RewriteStrategy, knowledge: Dict[str, Any]) -> List[EditOperation]:
        prompt = f"""
        You are an expert Resume Editor. Your job is to output structured edit operations (rewrite, move, expand, compress) to tailor a resume.
        You MUST NEVER invent technologies, metrics, or responsibilities. You may ONLY reword existing facts to highlight relevance.
        
        REWRITE STRATEGY:
        Priority Skills: {', '.join(strategy.priority_skills)}
        Tone: {strategy.tone}
        Focus on Projects: {', '.join(strategy.sections_to_prioritize)}
        
        KNOWLEDGE:
        {json.dumps(knowledge.get('projects', []), indent=2)}
        
        OUTPUT FORMAT (JSON list only, no markdown blocks):
        [
          {{
            "action": "rewrite",
            "project_id": "proj_1",
            "bullet_index": 0,
            "new_text": "Rewritten text incorporating priority skills.",
            "reason": "Matched priority skill Python"
          }}
        ]
        
        Return ONLY valid JSON.
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.router.chat_completion(messages=messages, temperature=0.1, response_format={"type": "json_object"})
        
        ops_data = []
        try:
            # Handle markdown if the model returns it despite instruction
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "operations" in parsed:
                ops_data = parsed["operations"]
            elif isinstance(parsed, list):
                ops_data = parsed
        except Exception as e:
            print(f"Error parsing LLM output: {e}")
            return []
            
        operations = []
        for op in ops_data[:self.max_bullets]:
            operations.append(EditOperation(
                action=op.get("action", "rewrite"),
                project_id=op.get("project_id", ""),
                bullet_index=op.get("bullet_index", 0),
                new_text=op.get("new_text"),
                from_index=op.get("from_index"),
                to_index=op.get("to_index"),
                reason=op.get("reason", "")
            ))
        return operations

    def apply_operations(self, knowledge: Dict[str, Any], ops: List[EditOperation]) -> Dict[str, Any]:
        import copy
        new_k = copy.deepcopy(knowledge)
        for op in ops:
            if op.action == "rewrite":
                for p in new_k.get('projects', []):
                    if p['id'] == op.project_id:
                        if 0 <= op.bullet_index < len(p['bullets']):
                            p['bullets'][op.bullet_index] = op.new_text
        return new_k
