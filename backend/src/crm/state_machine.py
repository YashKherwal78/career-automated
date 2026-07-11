from src.system.logger import setup_logger
logger = setup_logger('state_machine')
from enum import Enum
from src.crm.database import add_or_update_lead

class PipelineStage(Enum):
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

def transition_state(company_name: str, new_stage: PipelineStage):
    add_or_update_lead(company_name, {"stage": new_stage.value})
    logger.info(f"[{company_name}] 🔄 Pipeline Stage Transition -> {new_stage.value}")
