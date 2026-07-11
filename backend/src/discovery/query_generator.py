class QueryGenerator:
    """
    Centralizes search query generation for job boards and search providers.
    """
    def __init__(self):
        self.target_roles = [
            "AI Engineer",
            "Applied AI Engineer",
            "LLM Engineer",
            "GenAI Engineer",
            "Product Manager",
            "Associate Product Manager",
            "Founder's Office"
        ]
        self.target_locations = [
            "India",
            "Remote India"
        ]
        self.experience_levels = [
            "Entry Level",
            "Junior",
            "0-2 Years"
        ]

    def generate_indeed_queries(self) -> list:
        queries = []
        for role in self.target_roles:
            queries.append({
                "q": role,
                "l": "India",
                "sc": "0kf:explvl(ENTRY_LEVEL);"
            })
        return queries

    def get_target_roles(self):
        return self.target_roles
