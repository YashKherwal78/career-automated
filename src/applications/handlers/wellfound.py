from src.system.logger import setup_logger
logger = setup_logger('wellfound')
import time
from .base import ApplicationHandler
from src.system.state import WorkflowState

class WellfoundHandler(ApplicationHandler):
    """
    Native Playwright handler for Wellfound 'Easy Apply' flows.
    """
    def can_handle(self, url: str) -> bool:
        return "wellfound.com" in url.lower() or "angel.co" in url.lower()
        
    def execute(self) -> WorkflowState:
        logger.info(f"WellfoundHandler: Executing Easy Apply flow for {self.url}...")
        
        # Check if Easy Apply is available
        if "easy_apply=false" in self.url:
            logger.info("WellfoundHandler: No Easy Apply available. Failing back to MANUAL_REVIEW.")
            return WorkflowState.REVIEW_REQUIRED
            
        logger.info("WellfoundHandler: Automation engine not yet linked for Wellfound. Cannot apply.")
        return WorkflowState.NOT_IMPLEMENTED
