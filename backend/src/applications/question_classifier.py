class QuestionClassifier:
    """
    Classifies application form questions and determines if they are safe to auto-answer
    using profile data or LLM, or if they must be escalated to REVIEW_REQUIRED.
    """
    
    # Kept in sync with question_engine.py's own canonical-field keyword
    # checks (QuestionEngine.answer()'s TYPE 1 block) — a keyword missing
    # here gets escalated by this classifier before ever reaching that
    # resolution logic, even though question_engine.py already knows how to
    # answer it (this exact gap caused "Current company"/"Number of years
    # of experience" to be wrongly escalated on real Lever/Ashby forms).
    DETERMINISTIC_FIELDS = [
        "first name", "last name", "email", "phone", "linkedin", "github",
        "portfolio", "website", "current city", "city", "location", "address",
        "country", "nationality", "based in", "reside",
        "work authorization", "sponsorship", "visa", "notice period",
        "graduation year", "degree", "qualification", "education",
        "university", "school", "college",
        "gender", "race", "veteran", "disability", "pronouns",
        "transgender", "hispanic", "latino", "criminal", "felony",
        "convicted", "conviction", "conflict of interest", "privacy",
        "acknowledg",
        "current company", "current employer", "current organization",
        "previous employer", "former employer", "employer", "organization",
        "preferred location", "office preference", "work location",
        "which office",
        "language", "speak", "proficienc",
        "start date", "earliest start", "latest start", "when can you start",
        "available to start", "available to join", "when can you join",
        "when are you available to join", "graduation date", "passout",
        "expected graduation", "end date",
        "years of experience", "how many years",
        "hear about", "source", "how did you find out",
        # Name variants. Ashby asks for these as custom questions rather than
        # system fields ("Legal Name (First Name Last Name)", "Preferred
        # Name"), and without them here the classifier escalated a question
        # the profile answers trivially. Specific phrases only — a bare "name"
        # would swallow "company name" / "manager's name" and wrongly mark
        # them deterministic.
        "legal name", "full name", "preferred name", "your name", "nickname",
        "middle name", "surname", "family name",
        # Relocation is a KNOCKOUT the profile answers outright, but it was
        # absent here, so "will you be able to relocate to Hyderabad and work
        # from the office?" got escalated before it ever reached the
        # resolution logic that already knows the answer.
        "relocate", "relocation", "willing to move", "work from the office",
        # Real Indian-market phrasings the US-centric keyword lists missed.
        "come to know about", "get to know about",
        "total work experience", "total experience", "when can you join",
        "by when can you join", "last working day",
    ]

    ESCALATION_KEYWORDS = [
        "salary", "compensation", "expectations",
        "why do you want to join", "why are you interested",
        "essay", "cover letter"
    ]

    # Free-text questions that ARE answerable from grounded profile/RAG
    # content rather than being open-ended opinion or negotiation.
    #
    # Rationale (2026-08-01 session): rule 4 below escalates every unrecognised
    # free-text question to REVIEW_REQUIRED. That rule exists to stop the LLM
    # hallucinating essays, which is right — but as written it also escalated
    # "Share a project you're especially proud of", a question the RAG index
    # answers directly from the candidate's own project write-ups. Since
    # essentially every real Ashby/Greenhouse form carries at least one such
    # question, the blanket rule meant no application could ever reach submit.
    #
    # The narrow exemption below only covers questions grounded in the
    # candidate's actual recorded experience, and the answer still passes
    # through QuestionEngine's existing metric-grounding validator (which
    # rejects any number not present in the retrieved context). Genuinely
    # ambiguous or negotiation-type questions — salary, "why this company",
    # cover letters — remain escalated via ESCALATION_KEYWORDS above, which is
    # checked first and therefore wins over this list.
    GROUNDED_FREETEXT_KEYWORDS = [
        "project", "tell us about your experience", "relevant experience",
        "describe your experience", "walk us through", "proud of",
        "what have you built", "something you built", "technical background",
        "briefly describe your background", "your background",
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
            
        # 3b. Grounded free-text — answerable from the candidate's own recorded
        # experience via RAG. Checked after the strict escalations above, so
        # anything matching both stays escalated.
        for keyword in cls.GROUNDED_FREETEXT_KEYWORDS:
            if keyword in q_lower:
                return "DETERMINISTIC"

        # 4. Unknown free-text questions -> Escalate to avoid hallucinating essays
        if widget_type in ["textarea", "input"]:
            return "ESCALATE"
            
        return "UNKNOWN"
