from src.system.logger import setup_logger
logger = setup_logger('greenhouse_board_discovery')
import requests
from src.crm.database import add_to_company_registry

class GreenhouseBoardDiscovery:
    def __init__(self):
        # A small bootstrap dataset is acceptable ONLY for testing.
        self.bootstrap_slugs = [
            "openai", "anthropic", "stripe", "scaleai", 
            "groww", "phonepe", "zepto", "navi", "slice", "figma"
        ]

    def verify_slug(self, slug: str) -> bool:
        """Pings the Greenhouse API to verify the board exists."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        return False

    def run(self):
        logger.info("GreenhouseBoardDiscovery: Starting board verification...")
        verified_count = 0
        for slug in self.bootstrap_slugs:
            if self.verify_slug(slug):
                if add_to_company_registry(slug):
                    logger.info(f"[VERIFIED] {slug} -> Added to Registry")
                    verified_count += 1
                else:
                    logger.info(f"[EXISTS] {slug} -> Already in Registry")
            else:
                logger.info(f"[FAILED] {slug} -> Board not found or inactive")
        logger.info(f"GreenhouseBoardDiscovery: Complete. Verified {verified_count} new boards.")

if __name__ == "__main__":
    discoverer = GreenhouseBoardDiscovery()
    discoverer.run()
