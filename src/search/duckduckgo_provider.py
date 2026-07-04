from duckduckgo_search import DDGS
from typing import List, Dict, Optional

class DuckDuckGoProvider:
    def __init__(self):
        self.ddgs = DDGS()

    def search_recruiters(self, company: str, max_results: int = 3) -> List[Dict]:
        """
        Searches DDG for recruiters at a specific company via LinkedIn X-Ray.
        """
        query = f"site:linkedin.com/in \"{company}\" \"Recruiter\" OR \"Talent Acquisition\""
        return self._execute_people_search(query, company, max_results, "Recruiter")

    def search_hiring_managers(self, company: str, role: str, max_results: int = 3) -> List[Dict]:
        """
        Searches DDG for potential hiring managers at a specific company.
        """
        query = f"site:linkedin.com/in \"{company}\" \"{role}\" AND (\"Manager\" OR \"Director\" OR \"Head\" OR \"Lead\")"
        return self._execute_people_search(query, company, max_results, "Hiring Manager")

    def discover_career_page(self, company: str) -> Optional[str]:
        """
        Searches DDG for the company's official career page.
        """
        query = f"\"{company}\" careers OR jobs"
        try:
            results = self.ddgs.text(query, max_results=3)
            for res in results:
                url = res.get("href", "")
                if url and "linkedin.com" not in url and "indeed.com" not in url and "glassdoor.com" not in url:
                    # Return the first direct link that looks like a career page
                    return url
        except Exception as e:
            print(f"[DDG Provider] Career page search failed for {company}: {e}")
        return None

    def _execute_people_search(self, query: str, company: str, max_results: int, default_type: str) -> List[Dict]:
        contacts = []
        try:
            results = self.ddgs.text(query, max_results=max_results)
            for res in results:
                title_text = res.get("title", "")
                url = res.get("href", "")
                
                # Cleanup typical DDG LinkedIn titles: "John Doe - Senior Recruiter - Stripe | LinkedIn"
                clean_title = title_text.replace(" | LinkedIn", "").split(" - ")
                name = clean_title[0].strip() if len(clean_title) > 0 else "Unknown"
                
                # The title might be the second or third element
                title = clean_title[1].strip() if len(clean_title) > 1 else default_type
                
                if "linkedin.com/in/" in url and name != "Unknown":
                    contacts.append({
                        "contact_name": name,
                        "job_title": title,
                        "company": company,
                        "linkedin_url": url,
                        "discovery_source": "DuckDuckGo X-Ray",
                        "contact_type": default_type
                    })
        except Exception as e:
            print(f"[DDG Provider] People search failed: {e}")
            
        return contacts
