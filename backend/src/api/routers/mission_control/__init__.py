from fastapi import APIRouter, Depends
from src.runtime.auth.dependencies import get_current_user, CurrentUser
import os

router = APIRouter()

def get_authorized_operator(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    allowed = os.getenv("ALLOWED_OPERATORS", "yash.kherwal78@gmail.com")
    allowed_list = [email.strip() for email in allowed.split(",")]
    if current_user.email not in allowed_list:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Operator access only."
        )
    return current_user

# Import sub-routers
from .overview import router as overview_router
from .connectors import router as connectors_router
from .workers import router as workers_router
from .scheduler import router as scheduler_router
from .queues import router as queues_router
from .pipeline import router as pipeline_router
from .companies import router as companies_router
from .crawls import router as crawls_router
from .events import router as events_router
from .logs import router as logs_router
from .tracing import router as tracing_router
from .database import router as database_router
from .redis import router as redis_router
from .deployments import router as deployments_router
from .alerts import router as alerts_router
from .ai import router as ai_router
from .search import router as search_router

router.include_router(overview_router, prefix="/overview", tags=["Mission Control Overview"], dependencies=[Depends(get_authorized_operator)])
router.include_router(connectors_router, prefix="/connectors", tags=["Mission Control Connectors"], dependencies=[Depends(get_authorized_operator)])
router.include_router(workers_router, prefix="/workers", tags=["Mission Control Workers"], dependencies=[Depends(get_authorized_operator)])
router.include_router(scheduler_router, prefix="/scheduler", tags=["Mission Control Scheduler"], dependencies=[Depends(get_authorized_operator)])
router.include_router(queues_router, prefix="/queues", tags=["Mission Control Queues"], dependencies=[Depends(get_authorized_operator)])
router.include_router(pipeline_router, prefix="/pipeline", tags=["Mission Control Pipeline"], dependencies=[Depends(get_authorized_operator)])
router.include_router(companies_router, prefix="/companies", tags=["Mission Control Companies"], dependencies=[Depends(get_authorized_operator)])
router.include_router(crawls_router, prefix="/crawls", tags=["Mission Control Crawls"], dependencies=[Depends(get_authorized_operator)])
router.include_router(events_router, prefix="/events", tags=["Mission Control Events"], dependencies=[Depends(get_authorized_operator)])
router.include_router(logs_router, prefix="/logs", tags=["Mission Control Logs"], dependencies=[Depends(get_authorized_operator)])
router.include_router(tracing_router, prefix="/tracing", tags=["Mission Control Tracing"], dependencies=[Depends(get_authorized_operator)])
router.include_router(database_router, prefix="/database", tags=["Mission Control Database"], dependencies=[Depends(get_authorized_operator)])
router.include_router(redis_router, prefix="/redis", tags=["Mission Control Redis"], dependencies=[Depends(get_authorized_operator)])
router.include_router(deployments_router, prefix="/deployments", tags=["Mission Control Deployments"], dependencies=[Depends(get_authorized_operator)])
router.include_router(alerts_router, prefix="/alerts", tags=["Mission Control Alerts"], dependencies=[Depends(get_authorized_operator)])
router.include_router(ai_router, prefix="/ai", tags=["Mission Control AI"], dependencies=[Depends(get_authorized_operator)])
router.include_router(search_router, prefix="/search", tags=["Mission Control Search"], dependencies=[Depends(get_authorized_operator)])
