from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_logs():
    return {
        "status": "Not Yet Instrumented",
        "description": "Log streaming and centralization has not been configured in the backend routing rules."
    }
