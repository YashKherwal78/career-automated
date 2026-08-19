from abc import ABC, abstractmethod
from typing import Dict, Any


def derive_diagnosis(telemetry: dict) -> str:
    """Human-readable reason a non-COMPLETED result stopped short, built
    from the telemetry fields base_handler.py's execute() already populates
    (escalated_questions, missing_fields, captcha_paused). Every adapter
    previously read telemetry.get("diagnosis_json", "") for failure_reason,
    but nothing ever set that key, so failure_reason was silently blank on
    every REVIEW_REQUIRED/FAILED result -- callers had no way to know why."""
    reasons = []
    if telemetry.get("captcha_paused"):
        reasons.append("A CAPTCHA challenge appeared and needs a human to solve it")
    for m in telemetry.get("missing_fields", []):
        reasons.append(
            f"Couldn't confidently answer required question: \"{m.get('question')}\" "
            f"(confidence {m.get('confidence')})"
        )
    for e in telemetry.get("escalated_questions", []):
        if e.get("required"):
            reasons.append(f"Complex required question needs a human answer: \"{e.get('question')}\"")
    if not reasons:
        error_text = telemetry.get("submission_proof", {}).get("error_text")
        if error_text:
            reasons.append(error_text)
    return "; ".join(reasons)


class ApplicationResult:
    def __init__(self, status: str, confirmation_url: str = "", screenshot_path: str = "", submitted_answers: Dict[str, Any] = None, failure_reason: str = "", really_submitted: bool = False, jd_source: str = ""):
        self.status = status # COMPLETED, FAILED, REVIEW_REQUIRED
        # Which JD-enrichment step actually produced the job description this
        # application was answered from ("db_match"/"form_description"/
        # "web_search"/"none"). Only adapters that run the fallback chain
        # themselves set it; empty means "the caller's own accounting stands".
        self.jd_source = jd_source
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
    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False, user_id: str = None) -> ApplicationResult:
        """
        Executes the application logic for a specific ATS connector.
        Returns an ApplicationResult indicating success or failure.
        `test_mode` is forwarded to the handler unchanged — when True, the
        handler runs the full fill/answer/audit cycle but stops before the
        final submit click (see BaseATSHandler.execute()).
        """
        pass
