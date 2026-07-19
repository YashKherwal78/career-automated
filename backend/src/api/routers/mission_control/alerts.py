from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_alerts():
    return [
        {"id": "alert-1", "severity": "WARNING", "title": "Heartbeat lost on Worker 4", "time": "2 minutes ago"}
    ]
