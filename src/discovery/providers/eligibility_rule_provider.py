import os
import yaml
import re
from dataclasses import dataclass
from typing import List, Tuple
from src.config.config import Config

@dataclass
class EligibilityRule:
    id: str
    priority: int
    action: str
    field: str
    match_type: str
    pattern: str
    compiled_regex: re.Pattern = None

class EligibilityRuleProvider:
    """
    Parses and serves Eligibility Rules from YAML.
    Separates rule logic from the storage and definition mechanism.
    """
    def __init__(self, rule_file_path: str = None):
        if not rule_file_path:
            rule_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "eligibility_rules.yaml")
        self.rule_file_path = rule_file_path
        self.version = "unknown"
        self.rules: List[EligibilityRule] = []
        self._load_and_compile()

    def _load_and_compile(self):
        if not os.path.exists(self.rule_file_path):
            raise FileNotFoundError(f"Eligibility rules file not found: {self.rule_file_path}")

        with open(self.rule_file_path, 'r') as f:
            data = yaml.safe_load(f)

        self.version = data.get("version", "1.0.0")
        raw_rules = data.get("rules", [])

        compiled = []
        for r in raw_rules:
            rule = EligibilityRule(
                id=r["id"],
                priority=r["priority"],
                action=r["action"],
                field=r["field"],
                match_type=r["match"],
                pattern=r["pattern"]
            )
            
            if rule.match_type == "regex":
                try:
                    rule.compiled_regex = re.compile(rule.pattern)
                except re.error as e:
                    raise ValueError(f"Invalid regex in rule {rule.id}: {rule.pattern}") from e
                    
            compiled.append(rule)

        # Sort rules by priority descending
        self.rules = sorted(compiled, key=lambda x: x.priority, reverse=True)

    def get_rules(self) -> Tuple[str, List[EligibilityRule]]:
        """
        Returns the version string and the ordered list of pre-compiled rules.
        """
        return self.version, self.rules
