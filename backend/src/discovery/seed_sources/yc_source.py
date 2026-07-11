import logging
import aiohttp
from typing import List, Dict, Any
from src.discovery.seed_sources.base import SeedSource

logger = logging.getLogger("YCombinatorSource")

class YCombinatorSource(SeedSource):
    name = "ycombinator"
    priority = 1
    enabled = True

    async def discover(self) -> List[Dict[str, Any]]:
        logger.info("Discovering company seeds from YCombinatorSource...")
        
        # High-confidence YC startup seeds to bootstrap discovery
        curated_yc_seeds = [
            {"company_id": "linear", "name": "Linear", "website": "https://linear.app", "source": "ycombinator", "confidence": 1.0},
            {"company_id": "posthog", "name": "PostHog", "website": "https://posthog.com", "source": "ycombinator", "confidence": 1.0},
            {"company_id": "stripe", "name": "Stripe", "website": "https://stripe.com", "source": "ycombinator", "confidence": 1.0},
            {"company_id": "reclaimprotocol", "name": "Reclaim Protocol", "website": "https://reclaimprotocol.org", "source": "ycombinator", "confidence": 0.95},
            {"company_id": "watsi", "name": "Watsi", "website": "https://watsi.org", "source": "ycombinator", "confidence": 0.9},
            {"company_id": "airware", "name": "Airware", "website": "https://airware.com", "source": "ycombinator", "confidence": 0.9},
            {"company_id": "laserfocus", "name": "Laserfocus", "website": "https://laserfocus.io", "source": "ycombinator", "confidence": 0.95},
            {"company_id": "sorce", "name": "Sorce", "website": "https://sorce.jobs", "source": "ycombinator", "confidence": 0.9},
            {"company_id": "marblism", "name": "Marblism", "website": "https://marblism.com", "source": "ycombinator", "confidence": 0.95},
            {"company_id": "skyrootaerospace", "name": "Skyroot Aerospace", "website": "https://skyrootaerospace.com", "source": "ycombinator", "confidence": 0.9},
            {"company_id": "testxyzcompany", "name": "Test XYZ Company", "website": "https://testxyzcompany.com", "source": "ycombinator", "confidence": 1.0},
        ]
        
        # In a real environment, we can also query the YC directory API or parse batch list pages:
        # e.g., using a public JSON list of YC startups
        yc_api_url = "https://raw.githubusercontent.com/algolia/datasets/master/ycombinator/companies.json"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(yc_api_url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        external_seeds = []
                        for item in data[:50]:  # Limit to 50 for safety
                            name = item.get("name")
                            url = item.get("website")
                            if name and url:
                                domain = url.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
                                company_id = domain.split(".")[0].lower()
                                external_seeds.append({
                                    "company_id": company_id,
                                    "name": name,
                                    "website": url,
                                    "source": "ycombinator",
                                    "confidence": 0.95
                                })
                        if external_seeds:
                            logger.info(f"Loaded {len(external_seeds)} seeds from Algolia YC Dataset.")
                            return external_seeds
        except Exception as e:
            logger.warning(f"Could not load Algolia YC dataset fallback: {e}. Using curated seeds.")
            
        return curated_yc_seeds
