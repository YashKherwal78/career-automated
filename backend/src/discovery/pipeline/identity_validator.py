import re
from typing import Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.discovery.pipeline.fallback_models import IdentityResult
from src.discovery.models import InspectionResult
from src.discovery.pipeline.http_client import HttpClient

class CompanyIdentityValidator:
    def __init__(self, http_client: HttpClient):
        self.http = http_client
        
    @staticmethod
    def _normalize(name: str) -> str:
        if not name:
            return ""
        name = name.lower()
        name = re.sub(r'\\b(inc|llc|ltd|corp|corporation|company)\\b\\.?', '', name)
        return re.sub(r'[^a-z0-9]', '', name)

    @staticmethod
    def pre_filter(target_company: str, candidate_url: str) -> bool:
        """
        Fast heuristic check. Returns False if obviously mismatched.
        """
        parsed = urlparse(candidate_url)
        hostname = parsed.hostname or ""
        
        target_norm = CompanyIdentityValidator._normalize(target_company)
        
        # Extract tenant for common ATS
        tenant = ""
        if "myworkdayjobs.com" in hostname or "apply.workday.com" in hostname:
            parts = hostname.split('.')
            if len(parts) > 2:
                tenant = parts[0]
        elif "greenhouse.io" in hostname:
            tenant = parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else ""
        elif "lever.co" in hostname:
            tenant = parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else ""
            
        tenant_norm = CompanyIdentityValidator._normalize(tenant)
        
        if not target_norm:
            return True
            
        # If the target name is somewhat in the hostname or tenant, it passes pre-filter
        host_norm = CompanyIdentityValidator._normalize(hostname)
        if target_norm in host_norm or target_norm in tenant_norm:
            return True
        if tenant_norm and tenant_norm in target_norm:
            return True
            
        # If target name is very long and part of it matches
        if len(target_norm) > 4:
            if target_norm[:5] in host_norm:
                return True
                
        # If it's a completely custom domain, allow it to pass to deep inspection
        if "workday" not in hostname and "greenhouse" not in hostname and "lever" not in hostname:
            return True
            
        return False

    async def validate(self, target_company: str, candidate_url: str, inspection: InspectionResult) -> IdentityResult:
        """
        Deep multi-signal verification using HTML and Inspector metadata.
        """
        matched = []
        failed = []
        score = 0.0
        
        target_norm = self._normalize(target_company)
        target_lower = target_company.lower()
        
        # 1. Inspector Metadata check
        if inspection.canonical_company:
            canon_norm = self._normalize(inspection.canonical_company)
            if target_norm in canon_norm or canon_norm in target_norm:
                score += 0.4
                matched.append(f"Inspector tenant '{inspection.canonical_company}' matches target.")
            else:
                failed.append(f"Inspector tenant '{inspection.canonical_company}' mismatch.")
                
        # 2. Fetch HTML branding
        try:
            # If it's workday CXS api URL, try to guess the frontend URL
            fetch_url = candidate_url
            if "/wday/cxs/" in fetch_url:
                parsed = urlparse(fetch_url)
                parts = parsed.path.strip('/').split('/')
                if len(parts) >= 4:
                    tenant = parts[2]
                    site = parts[3]
                    fetch_url = f"https://{parsed.hostname}/{site}"
                    
            res = await self.http.fetch('GET', fetch_url)
            if res and res.payload:
                html = res.payload.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Title
                title_tag = soup.find('title')
                title_text = title_tag.text.lower() if title_tag else ""
                if target_lower in title_text:
                    score += 0.3
                    matched.append(f"Title contains '{target_company}'")
                elif title_text:
                    failed.append(f"Title mismatch: '{title_text}'")
                    
                # OG Metadata
                og_title = soup.find('meta', property='og:title')
                og_title_text = og_title['content'].lower() if og_title and og_title.get('content') else ""
                if target_lower in og_title_text:
                    score += 0.2
                    matched.append(f"OG:Title contains '{target_company}'")
                    
                og_desc = soup.find('meta', property='og:description')
                og_desc_text = og_desc['content'].lower() if og_desc and og_desc.get('content') else ""
                if target_lower in og_desc_text:
                    score += 0.3
                    matched.append(f"OG:Description contains '{target_company}'")
                elif og_desc_text:
                    failed.append("OG:Description mismatch")
                    
                # JSON-LD Check
                for script in soup.find_all('script', type='application/ld+json'):
                    if target_lower in script.text.lower():
                        score += 0.2
                        matched.append(f"JSON-LD contains '{target_company}'")
                        break
                        
        except Exception as e:
            failed.append(f"HTML fetch error: {e}")
            
        # 3. Final Decision
        confidence = min(1.0, score)
        if confidence >= 0.3:
            return IdentityResult(confidence=confidence, matched_signals=matched, failed_signals=failed, reason="High confidence match")
        else:
            return IdentityResult(confidence=confidence, matched_signals=matched, failed_signals=failed, reason="Confidence too low")
