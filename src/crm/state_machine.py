from enum import Enum
from src.crm.database import add_or_update_lead

class CRMState(Enum):
    NEW = "NEW"
    ENRICHED = "ENRICHED"
    SCORED = "SCORED"
    RESUME_SELECTED = "RESUME_SELECTED"
    RESUME_TAILORED = "RESUME_TAILORED"
    OUTBOX_QUEUE = "OUTBOX_QUEUE"
    HR_CONTACTED = "HR_CONTACTED"
    HR_REPLIED = "HR_REPLIED"
    FOUNDER_CONTACTED = "FOUNDER_CONTACTED"
    FOUNDER_REPLIED = "FOUNDER_REPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    HARD_BOUNCE = "HARD_BOUNCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

def transition_state(company_name: str, new_state: CRMState):
    add_or_update_lead(company_name, {"status": new_state.value})
    print(f"[{company_name}] 🔄 State Transition -> {new_state.value}")
