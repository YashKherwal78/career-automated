from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_events():
    return [
        {"timestamp": "2026-07-19T21:12:00Z", "event": "Worker 3 restarted", "severity": "INFO"},
        {"timestamp": "2026-07-19T21:10:00Z", "event": "Greenhouse Crawler completed for Stripe", "severity": "SUCCESS"},
        {"timestamp": "2026-07-19T20:45:00Z", "event": "Rate limit 429 encountered on Recruitee", "severity": "WARNING"}
    ]
