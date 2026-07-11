class QuestionClassifier:
    """
    Classifies application form questions and determines if they are safe to auto-answer
    using profile data or LLM, or if they must be escalated to REVIEW_REQUIRED.
    """
    
    DETERMINISTIC_FIELDS = [
        "first name", "last name", "email", "phone", "linkedin", "github", 
        "portfolio", "website", "current city", "location", "address",
        "work authorization", "sponsorship", "visa", "notice period",
        "graduation year", "degree", "university", "school", "college",
        "gender", "race", "veteran", "disability", "pronouns"
    ]
    
    ESCALATION_KEYWORDS = [
        "salary", "compensation", "expectations", 
        "why do you want to join", "why are you interested",
        "essay", "cover letter"
    ]

    @classmethod
    def classify(cls, question: str, widget_type: str) -> str:
        """
        Returns: 'DETERMINISTIC', 'ESCALATE', or 'UNKNOWN'
        """
        q_lower = question.lower()
        
        # 1. Check strict escalations first
        for keyword in cls.ESCALATION_KEYWORDS:
            if keyword in q_lower:
                return "ESCALATE"
                
        # 2. Check deterministic fields
        for field in cls.DETERMINISTIC_FIELDS:
            if field in q_lower:
                return "DETERMINISTIC"
                
        # 3. If it's a dropdown/multiselect/radio, it's generally safe to try LLM
        if widget_type in ["react_select", "native_select", "radio_group", "checkbox_group"]:
            return "DETERMINISTIC" # Let the LLM guess based on constrained options
            
        # 4. Unknown free-text questions -> Escalate to avoid hallucinating essays
        if widget_type in ["textarea", "input"]:
            return "ESCALATE"
            
        return "UNKNOWN"
