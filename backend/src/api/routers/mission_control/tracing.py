from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_traces():
    return {
        "status": "Not Yet Instrumented",
        "description": "Distributed tracing OpenTelemetry trace captures are not active in this environment."
    }
