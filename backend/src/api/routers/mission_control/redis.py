from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_redis():
    return {
        "status": "Not Yet Instrumented",
        "description": "Redis cluster telemetry connection has not been exposed."
    }
