from src.discovery.models import Candidate, InspectionResult

def rank_candidate(candidate: Candidate, inspection: InspectionResult, expected_company: str) -> tuple:
    """
    Returns a sortable tuple representing the strength of the evidence.
    Python sorts tuples lexicographically, so earlier elements have higher precedence.
    True > False, so a True condition ranks higher than a False condition.
    """
    
    # Identify if the company name roughly matches the canonical name from the ATS API
    canonical = str(inspection.canonical_company or "").lower()
    expected = expected_company.lower()
    
    # Very basic company match (could be improved with fuzzy matching later)
    # E.g. expected="Figma", canonical="Figma, Inc." -> Match
    company_match = (expected in canonical) if canonical else False
    
    # A candidate is considered fully verified if it exists, has jobs, 
    # and either the API name matches OR there was no API name to check (but it still responded to the API).
    # Wait, the prompt said: "company_match = (expected_company.lower() in str(inspection.canonical_company).lower())"
    # and "is_verified = (inspection.api_verified and company_match and inspection.board_exists)"
    
    is_verified = bool(inspection.api_verified and company_match and inspection.board_exists)
    
    return (
        is_verified,                   # 1. Must pass basic verification policy
        bool(inspection.api_verified), # 2. Did a native API confirm it?
        bool(company_match),           # 3. Did the API confirm the company name?
        bool(inspection.job_count > 0),# 4. Are there actually jobs?
        candidate.source == "crawler", # 5. Provenance: found directly on website
        candidate.source == "pattern_guess", # 6. Provenance: explicit pattern
    )
