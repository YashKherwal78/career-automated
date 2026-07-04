from abc import ABC, abstractmethod
from typing import Dict, Any

class ApplicationResult:
    def __init__(self, status: str, confirmation_url: str = "", screenshot_path: str = "", submitted_answers: Dict[str, Any] = None, failure_reason: str = ""):
        self.status = status # SUBMITTED, FAILED, REVIEW_REQUIRED
        self.confirmation_url = confirmation_url
        self.screenshot_path = screenshot_path
        self.submitted_answers = submitted_answers or {}
        self.failure_reason = failure_reason

class BaseAdapter(ABC):
    @abstractmethod
    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any) -> ApplicationResult:
        """
        Executes the application logic for a specific ATS connector.
        Returns an ApplicationResult indicating success or failure.
        """
        pass
