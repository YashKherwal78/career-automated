class ProjectSelector:
    @staticmethod
    def select(domain: str) -> tuple[str, list[str], str, str]:
        """
        Returns (Project, Rejected_Projects, Reasoning, Confidence)
        """
        domain_lower = domain.lower()
        
        gdsc_keywords = ["search", "rag", "retrieval", "information extraction"]
        yaar_keywords = ["advertising", "marketing", "media", "consumer", "creator", "engagement", "personalization", "entertainment", "social"]
        career_keywords = ["ai", "genai", "manufacturing", "ev", "automotive", "industrial", "operations", "supply chain", "logistics", "automation"]
        
        all_projects = {"CareerAutomated", "YAAR", "GDSC Search Engine"}
        
        # Determine candidate
        for k in career_keywords:
            if k in domain_lower:
                return ("CareerAutomated", list(all_projects - {"CareerAutomated"}), f"Matched AI/Industrial keyword: '{k}'", "High")
                
        for k in yaar_keywords:
            if k in domain_lower:
                return ("YAAR", list(all_projects - {"YAAR"}), f"Matched Consumer/Media keyword: '{k}'", "High")
                
        for k in gdsc_keywords:
            if k in domain_lower:
                return ("GDSC Search Engine", list(all_projects - {"GDSC Search Engine"}), f"Matched Search/RAG keyword: '{k}'", "High")
                
        # Default fallback
        return ("GDSC Search Engine", list(all_projects - {"GDSC Search Engine"}), "Default fallback applied for unrecognized domain", "Low")
