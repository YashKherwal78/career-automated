from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_scheduler():
    return {
        "status": "ACTIVE",
        "running_jobs": 2,
        "upcoming_jobs": 15,
        "delayed_jobs": 0,
        "adaptive_scheduling": "ENABLED"
    }
