from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_ai():
    return {
        "status": "Not Yet Instrumented",
        "description": "Token usage and AI tailoring telemetry has not been instrumented."
    }
