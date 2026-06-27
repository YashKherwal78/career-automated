from typing import List, Dict
from src.discovery.providers.company_search_provider import CompanySearchProvider
from src.discovery.ats_detector import ATSDetector
from src.crm.database import get_connection

class CompanyDiscoveryEngine:
    def __init__(self):
        self.search_provider = CompanySearchProvider()
        self.ats_detector = ATSDetector()

    def run_discovery(self) -> Dict:
        print("CompanyDiscoveryEngine: Starting slow loop scan...")
        discovered_urls = self.search_provider.discover_startups()
        
        stats = {
            "new_companies": 0,
            "ats_detected": 0,
            "careers_page_found": len(discovered_urls),
            "unknown_ats": 0,
            "skipped": 0
        }
        
        conn = get_connection()
        c = conn.cursor()
        
        for url in discovered_urls:
            detection = self.ats_detector.detect_ats(url)
            
            if detection["ats_provider"] != "unknown":
                stats["ats_detected"] += 1
                ats = detection["ats_provider"]
                slug = detection["slug"]
                
                # Mocking company name for simplicity if we don't fetch the title tag
                company_name = slug.capitalize() if slug else "Unknown"
                
                gh_slug = slug if ats == "greenhouse" else None
                lever_slug = slug if ats == "lever" else None
                ashby_slug = slug if ats == "ashby" else None
                
                try:
                    c.execute('''
                        INSERT OR IGNORE INTO company_intelligence_static 
                        (company_name, careers_url, ats_provider, greenhouse_slug, lever_slug, ashby_slug, lifecycle_status)
                        VALUES (?, ?, ?, ?, ?, ?, 'VERIFIED')
                    ''', (company_name, url, ats, gh_slug, lever_slug, ashby_slug))
                    stats["new_companies"] += 1
                except Exception as e:
                    stats["skipped"] += 1
            else:
                stats["unknown_ats"] += 1
                
        conn.commit()
        conn.close()
        
        return stats
