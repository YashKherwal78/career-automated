import re
from typing import Dict, Any

# Simple regex-based dictionaries for location classification
COUNTRIES = {
    "united states": "United States", "usa": "United States", "us": "United States",
    "india": "India", "in": "India",
    "united kingdom": "United Kingdom", "uk": "United Kingdom", "gb": "United Kingdom",
    "germany": "Germany", "de": "Germany",
    "canada": "Canada", "ca": "Canada",
}

STATES = {
    # US States
    "california": "California", "ca": "California",
    "new york": "New York", "ny": "New York",
    "texas": "Texas", "tx": "Texas",
    "washington": "Washington", "wa": "Washington",
    # Indian States
    "karnataka": "Karnataka", "ka": "Karnataka",
    "maharashtra": "Maharashtra", "mh": "Maharashtra",
    "telangana": "Telangana", "ts": "Telangana",
    "haryana": "Haryana", "hr": "Haryana",
}

CITIES = {
    "san francisco": "San Francisco", "new york city": "New York", "nyc": "New York",
    "seattle": "Seattle", "austin": "Austin", "los angeles": "Los Angeles",
    "bangalore": "Bangalore", "bengaluru": "Bangalore",
    "mumbai": "Mumbai", "pune": "Pune", "hyderabad": "Hyderabad",
    "gurgaon": "Gurgaon", "gurugram": "Gurgaon", "noida": "Noida",
    "london": "London", "berlin": "Berlin", "munich": "Munich",
}

def extract_location(text: str, title: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts country, state, city, and determines work mode (Remote/Hybrid/Onsite)."""
    loc_info = {"country": "", "state": "", "city": ""}
    
    # Try finding location string from metadata or text
    loc_str = metadata.get("location") or ""
    
    if not loc_str:
        # Search for pattern like "Location: San Francisco, CA"
        loc_match = re.search(r'(?:location|loc):\s*([^\n,]+)(?:,\s*([^\n,]+))?(?:,\s*([^\n,]+))?', text, re.IGNORECASE)
        if loc_match:
            parts = [p.strip() for p in loc_match.groups() if p]
            loc_str = ", ".join(parts)
            
    # Resolve Country, State, City from the location string
    if loc_str:
        parts = [p.strip().lower() for p in loc_str.split(",")]
        for part in parts:
            if part in CITIES:
                loc_info["city"] = CITIES[part]
            elif part in STATES:
                loc_info["state"] = STATES[part]
            elif part in COUNTRIES:
                loc_info["country"] = COUNTRIES[part]
                
    # Determine work mode
    work_mode = "Unknown"
    text_lower = text.lower() + " " + title.lower()
    
    if re.search(r'\b(remote|work\s+from\s+home|wfh|anywhere)\b', text_lower):
        work_mode = "Remote"
    elif re.search(r'\b(hybrid|flexible\s+onsite|partial\s+remote)\b', text_lower):
        work_mode = "Hybrid"
    elif re.search(r'\b(onsite|on-site|in-office|in\s+office|office-based)\b', text_lower):
        work_mode = "Onsite"
        
    return {
        "location": loc_info,
        "work_mode": work_mode
    }
