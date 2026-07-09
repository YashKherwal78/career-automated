from src.system.logger import setup_logger
logger = setup_logger('greenhouse_board_provider')
from typing import List
from src.crm.database import get_active_greenhouse_slugs

class GreenhouseBoardProvider:
    """
    Dedicated provider responsible for querying the Company Registry
    and supplying active, verified Greenhouse board slugs.
    """
    def __init__(self):
        pass

    def get_verified_slugs(self) -> List[str]:
        """
        Reads ACTIVE board slugs from company_registry that meet
        the confidence score thresholds.
        """
        logger.info("GreenhouseBoardProvider: Fetching verified slugs from registry...")
        slugs = get_active_greenhouse_slugs()
        logger.info(f"GreenhouseBoardProvider: Found {len(slugs)} active slugs.")
        return slugs
