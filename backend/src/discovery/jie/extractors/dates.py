import re
from typing import Optional, Dict

def extract_dates(text: str) -> Dict[str, Optional[str]]:
    """Extracts posted date and application deadline if present in the text."""
    dates = {"posted_date": None, "application_deadline": None}
    
    # 1. Posted Date matches: "Posted: 2026-07-20", "Posted: 3 days ago"
    posted_match = re.search(r'(?:posted|published|created\s*at):\s*([^\n]+)', text, re.IGNORECASE)
    if posted_match:
        dates["posted_date"] = posted_match.group(1).strip()
        
    # 2. Deadline matches: "Deadline: 2026-08-15", "Apply before: Aug 20"
    deadline_match = re.search(r'(?:deadline|apply\s+before|application\s+deadline):\s*([^\n]+)', text, re.IGNORECASE)
    if deadline_match:
        dates["application_deadline"] = deadline_match.group(1).strip()
        
    return dates
