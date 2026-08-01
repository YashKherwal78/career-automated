from abc import ABC, abstractmethod
from typing import Dict, Any

class ApplicationResult:
    def __init__(self, status: str, confirmation_url: str = "", screenshot_path: str = "", submitted_answers: Dict[str, Any] = None, failure_reason: str = "", really_submitted: bool = False):
        self.status = status # COMPLETED, FAILED, REVIEW_REQUIRED
        self.confirmation_url = confirmation_url
        self.screenshot_path = screenshot_path
        self.submitted_answers = submitted_answers or {}
        self.failure_reason = failure_reason
        # The only trustworthy answer to "was this actually submitted?" —
        # status == "COMPLETED" alone is ambiguous, since test_mode also
        # reaches COMPLETED without ever clicking submit. True only for a
        # real, non-test_mode run the verifier independently confirmed.
        self.really_submitted = really_submitted

class BaseAdapter(ABC):
    @abstractmethod
    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False) -> ApplicationResult:
        """
        Executes the application logic for a specific ATS connector.
        Returns an ApplicationResult indicating success or failure.
        `test_mode` is forwarded to the handler unchanged — when True, the
        handler runs the full fill/answer/audit cycle but stops before the
        final submit click (see BaseATSHandler.execute()).
        """
        pass
