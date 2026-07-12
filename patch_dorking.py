import re

with open("src/discovery/providers/google_dorking.py", "r") as f:
    content = f.read()

# Replace the inner fetch_dork with a class method and update discover_companies to call it
new_content = """import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import urllib.parse
from src.discovery.providers.base_provider import BaseProvider
from src.discovery.providers.provider_registry import ProviderRegistry
import asyncio

class GoogleDorkingProvider(BaseProvider):
    
    @property
    def provider_name(self) -> str:
        return "google_dorks"
        
    async def fetch_dork(self, dork: str, pages: int = 5) -> List[str]:
        urls = []
        try:
            import primp
            import re
            client = primp.Client(impersonate='chrome_120')
            
            # Fetch up to `pages` of Bing results per dork
            for page in range(pages):
                offset = 1 + (page * 10)
                search_url = f"https://www.bing.com/search?q={urllib.parse.quote(dork)}&first={offset}"
                response = client.get(search_url)
                
                if response.status_code == 200:
                    matches = re.findall(r'https://[a-zA-Z0-9-]+\.wd[1-5]\.myworkdayjobs\.com[a-zA-Z0-9_/-]*', response.text)
                    for match in matches:
                        # Trim to domain + tenant path
                        urls.append(match)
                        
                # Polite delay
                await asyncio.sleep(1)
        except Exception as e:
            print(f"[GoogleDorkingProvider] Error fetching {dork}: {e}")
            
        return urls
        
    async def discover_companies(self) -> List[Dict[str, Any]]:
        \"\"\"
        Executes Google Dorks via DuckDuckGo HTML (to avoid immediate CAPTCHAs) 
        and extracts Workday URLs.
        \"\"\"
        dorks = [
            "site:myworkdayjobs.com",
            "site:wd3.myworkdayjobs.com",
            "site:wd5.myworkdayjobs.com"
        ]
            
        discovered_urls = set()
        
        for dork in dorks:
            urls = await self.fetch_dork(dork)
            discovered_urls.update(urls)
                    
        results = []
        for url in discovered_urls:
            # Extract tenant name as a fallback company name
            domain = url.split("://")[-1].split("/")[0]
            tenant = domain.split(".")[0]
            
            results.append({
                "company_name": tenant.capitalize(),
                "careers_url": url,
                "ats_provider": "workday"
            })
            
        return results
        
    async def validate(self, session: Any, url: str) -> bool:
        \"\"\"
        Pings the URL and verifies Workday signatures (HTTP 406 or DOM markers).
        This keeps Workday-specific logic out of the main Discovery Engine.
        \"\"\"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                # Workday often returns 406 Not Acceptable to basic python bots
                if response.status == 406 and "myworkdayjobs.com" in str(response.url):
                    return True
                if response.status != 200:
                    return False
                    
                html = await response.text()
                # A true Workday career site has specific JS globals or DOM elements
                if "wday/cxs" in html or "workday-client" in html or "myworkdayjobs.com" in str(response.url):
                    return True
                return False
        except Exception:
            return False

ProviderRegistry.register(GoogleDorkingProvider)
"""

with open("src/discovery/providers/google_dorking.py", "w") as f:
    f.write(new_content)
