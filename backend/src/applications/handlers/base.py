from src.system.state import WorkflowState
    
class ApplicationHandler:
    def __init__(self, url: str):
        self.url = url
        
    def can_handle(self, url: str) -> bool:
        return False
        
    def execute(self) -> WorkflowState:
        return WorkflowState.REVIEW_REQUIRED
