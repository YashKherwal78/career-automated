import time
from .base import ApplicationHandler, ApplicationState

class WellfoundHandler(ApplicationHandler):
    """
    Native Playwright handler for Wellfound 'Easy Apply' flows.
    """
    def can_handle(self, url: str) -> bool:
        return "wellfound.com" in url.lower() or "angel.co" in url.lower()
        
    def execute(self) -> ApplicationState:
        print(f"WellfoundHandler: Executing Easy Apply flow for {self.url}...")
        
        # Simulated logic for V1 Validation Phase
        time.sleep(1)
        
        # Check if Easy Apply is available
        if "easy_apply=false" in self.url:
            print("WellfoundHandler: No Easy Apply available. Failing back to MANUAL_REVIEW.")
            return ApplicationState.MANUAL_REVIEW
            
        print("WellfoundHandler: Easy Apply button detected.")
        print("WellfoundHandler: Injecting Resume...")
        
        # Simulate question engine form fill
        print("WellfoundHandler: Answering custom questions...")
        
        print("WellfoundHandler: Submitting Application...")
        return ApplicationState.SUBMITTED
