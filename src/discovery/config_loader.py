import yaml
import re
from typing import Dict, Any

class CompiledRegexCache:
    def __init__(self, raw_config: Dict[str, Any]):
        self.version = raw_config.get("intent_config_version", 1)
        
        # Compile hard rejects
        hard = raw_config.get("hard_reject", {})
        self.hard_titles = [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in hard.get("titles", [])]
        self.hard_seniority = [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in hard.get("seniority", [])]
        
        # Compile role families
        self.families = {}
        for family, data in raw_config.get("role_families", {}).items():
            compiled_data = {
                "thresholds": data.get("thresholds", {"accept": 10, "review": 4}),
                "positive": [(re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v, k) for k, v in data.get("positive", {}).items()],
                "bonus": [(re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v, k) for k, v in data.get("bonus", {}).items()],
                "negative": [(re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v, k) for k, v in data.get("negative", {}).items()],
                "company_signals": data.get("company_signals", {})
            }
            self.families[family.lower()] = compiled_data

class ConfigLoader:
    _instance = None
    _cache = None
    
    @classmethod
    def get_intent_config(cls, filepath: str = "config/intent.yaml") -> CompiledRegexCache:
        if cls._cache is None:
            with open(filepath, 'r') as f:
                raw = yaml.safe_load(f)
            cls._cache = CompiledRegexCache(raw)
        return cls._cache
