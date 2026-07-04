from enum import Enum

class ApplicationState(Enum):
    SUBMITTED = 1
    MANUAL_REVIEW = 2
    REVIEW_REQUIRED = 3
    PAUSED = 4
    
class ApplicationHandler:
    def __init__(self, url: str):
        self.url = url
        
    def can_handle(self, url: str) -> bool:
        return False
        
    def execute(self) -> ApplicationState:
        return ApplicationState.MANUAL_REVIEW
