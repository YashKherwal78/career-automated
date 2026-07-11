import re

class ExperienceNormalizer:
    def __init__(self):
        # Entry level / 0 experience signals
        self.entry_level = [
            "0 years", "0-1 years", "0-2 years", "entry level", 
            "new grad", "graduate", "fresher", "freshers", 
            "associate", "early career", "junior", "0-3 years"
        ]
        
        self.mid_level = [
            "2-4 years", "3-5 years", "mid-level", "mid level", "experienced"
        ]
        
        self.senior_level = [
            "5+ years", "5-7 years", "senior", "lead", "principal", "director"
        ]

    def normalize(self, raw_experience: str, job_title: str) -> str:
        raw_lower = str(raw_experience).lower()
        title_lower = str(job_title).lower()
        
        # Check explicit title signals first
        for term in self.senior_level:
            if term in title_lower:
                return "SENIOR"
                
        for term in self.entry_level:
            if term in title_lower:
                return "ENTRY_LEVEL"

        # Check experience string
        if not raw_lower or raw_lower == "unknown":
            return "UNKNOWN"
            
        for term in self.senior_level:
            if term in raw_lower:
                return "SENIOR"
                
        for term in self.mid_level:
            if term in raw_lower:
                return "MID_LEVEL"
                
        for term in self.entry_level:
            if term in raw_lower:
                return "ENTRY_LEVEL"
                
        # Regex catch for digit-digit years
        digits = re.findall(r'(\d+)', raw_lower)
        if digits:
            lowest_req = int(digits[0])
            if lowest_req <= 2:
                return "ENTRY_LEVEL"
            elif lowest_req <= 4:
                return "MID_LEVEL"
            else:
                return "SENIOR"
                
        return "UNKNOWN"
