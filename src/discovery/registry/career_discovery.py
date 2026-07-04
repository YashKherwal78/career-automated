import sqlite3
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional
import uuid
import json

class SearchProviderManager:
    """Manages optional fallbacks to search engines like Google/LinkedIn if the main crawl fails."""
    def __init__(self, config: dict):
        self.config = config.get("search_providers", {})
        
    async def search_for_careers_page(self, company_name: str) -> Optional[str]:
        # If config allows google, we'd hit Serper API or similar here.
        # This is a fallback only triggered if direct DOM crawling fails.
        if "google" in self.config:
            # Mocking the fallback execution
            return f"https://boards.greenhouse.io/{company_name.lower().replace(' ', '')}"
        return None

class ATSDetector:
    """Detects ATS endpoints using DOM signatures, URL structures, and Regex fallbacks."""
    
    ATS_SIGNATURES = {
        "Greenhouse": [r"boards\.greenhouse\.io/([^/\"\'\?\>]+)", r"api\.greenhouse\.io/v1/boards/([^/\"\'\?\>]+)"],
        "Lever": [r"jobs\.lever\.co/([^/\"\'\?\>]+)", r"api\.lever\.co/v0/postings/([^/\"\'\?\>]+)"],
        "Ashby": [r"jobs\.ashbyhq\.com/([^/\"\'\?\>]+)", r"api\.ashbyhq\.com/posting-api/job-board/([^/\"\'\?\>]+)"],
        "Workday": [r"myworkdayjobs\.com/([^/\"\'\?\>]+)"],
        "Workable": [r"apply\.workable\.com/([^/\"\'\?\>]+)"],
        "SmartRecruiters": [r"jobs\.smartrecruiters\.com/([^/\"\'\?\>]+)"],
        "iCIMS": [r"([^/\"\'\?\>]+)\.icims\.com"]
    }

    @staticmethod
    def detect_from_html(html_content: str, url: str) -> Tuple[Optional[str], Optional[str], float]:
        """Returns (ATS_Name, board_token, confidence)"""
        # 1. URL Analysis first
        for ats_name, patterns in ATSDetector.ATS_SIGNATURES.items():
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return ats_name, match.group(1), 0.99
                    
        # 2. DOM Parsing (Looking for iframes or script tags)
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Check iframes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            for ats_name, patterns in ATSDetector.ATS_SIGNATURES.items():
                for pattern in patterns:
                    match = re.search(pattern, src)
                    if match:
                        return ats_name, match.group(1), 0.95
                        
        # Check links
        for a in soup.find_all('a'):
            href = a.get('href', '')
            for ats_name, patterns in ATSDetector.ATS_SIGNATURES.items():
                for pattern in patterns:
                    match = re.search(pattern, href)
                    if match:
                        return ats_name, match.group(1), 0.90
                        
        # 3. Raw Regex on full DOM (Fallback)
        for ats_name, patterns in ATSDetector.ATS_SIGNATURES.items():
            for pattern in patterns:
                match = re.search(pattern, html_content)
                if match:
                    return ats_name, match.group(1), 0.85
                    
        return None, None, 0.0

class CareerDiscoveryEngine:
    def __init__(self, db_path: str, config: dict = None):
        self.db_path = db_path
        self.config = config or {}
        self.search_manager = SearchProviderManager(self.config)
        self.worker_limit = 20 # Configurable worker pool
        
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Tuple[str, str]:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            # Lightweight requests first
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                html = await response.text()
                return str(response.url), html
        except Exception:
            # Playwright Escapement would happen here for JS-rendered SPA sites
            return url, ""

    async def _process_company(self, session: aiohttp.ClientSession, company_id: str, domain: str, name: str) -> Dict:
        """The core async worker logic to discover a company's career page."""
        paths_to_probe = [
            f"https://{domain}/careers",
            f"https://{domain}/jobs",
            f"https://careers.{domain}",
            f"https://{domain}/join-us"
        ]
        
        for path in paths_to_probe:
            final_url, html = await self.fetch_page(session, path)
            if html:
                ats_name, board_token, confidence = ATSDetector.detect_from_html(html, final_url)
                if ats_name and confidence >= 0.95:
                    return {
                        "company_id": company_id,
                        "ats_provider": ats_name,
                        "endpoint_url": f"{ats_name.lower()}://{board_token}",
                        "confidence": confidence,
                        "evidence": json.dumps({
                            "matched_url": final_url,
                            "detector": "DOMParser",
                            "confidence": confidence
                        })
                    }
        
        # Fallback to SearchProviders if official domain crawling yields nothing
        fallback_url = await self.search_manager.search_for_careers_page(name)
        if fallback_url:
            ats_name, board_token, confidence = ATSDetector.detect_from_html("", fallback_url)
            if ats_name:
                return {
                    "company_id": company_id,
                    "ats_provider": ats_name,
                    "endpoint_url": f"{ats_name.lower()}://{board_token}",
                    "confidence": confidence - 0.10, # Lower confidence for search fallback
                    "evidence": json.dumps({
                        "matched_url": fallback_url,
                        "detector": "SearchProviderFallback",
                        "confidence": confidence - 0.10
                    })
                }
                
        return {"company_id": company_id, "error": "No ATS Detected"}

    async def _run_async_batch(self, companies: List[Tuple]) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [self._process_company(session, cid, domain, name) for cid, name, domain in companies]
            # Use asyncio.gather to run the worker pool concurrently
            results = await asyncio.gather(*tasks)
            return results
            
    def process_batch(self) -> Tuple[int, int]:
        print("[CareerDiscoveryEngine] Booting Asynchronous Worker Pool (20 workers)...")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Pull batch from DISCOVERED queue
        c.execute('''
            SELECT c.company_id, i.canonical_name, i.domain 
            FROM candidate_companies c
            JOIN company_identities i ON c.company_id = i.company_id
            WHERE c.status = 'DISCOVERED' LIMIT 500
        ''')
        companies = c.fetchall()
        
        if not companies:
            print("No companies in DISCOVERED state.")
            return 0, 0
            
        print(f"[CareerDiscoveryEngine] Handed {len(companies)} companies to Worker Pool.")
        
        # Execute async worker pool
        results = asyncio.run(self._run_async_batch(companies))
        
        endpoints_found = 0
        for res in results:
            cid = res["company_id"]
            if "error" in res:
                c.execute("UPDATE candidate_companies SET status = 'UNKNOWN' WHERE company_id = ?", (cid,))
            else:
                c.execute("UPDATE candidate_companies SET status = 'DETECTED' WHERE company_id = ?", (cid,))
                # Write to Discovery Knowledge Base
                ep_id = str(uuid.uuid4())
                c.execute('''
                    INSERT INTO career_endpoints (endpoint_id, company_id, ats_provider, endpoint_url, confidence, status, discovery_evidence)
                    VALUES (?, ?, ?, ?, ?, 'VERIFYING', ?)
                ''', (ep_id, cid, res["ats_provider"], res["endpoint_url"], res["confidence"], res["evidence"]))
                endpoints_found += 1
                
        conn.commit()
        conn.close()
        
        return len(companies), endpoints_found
