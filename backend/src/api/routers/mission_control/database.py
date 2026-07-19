from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_database():
    return {
        "status": "HEALTHY",
        "connections_active": 8,
        "connections_max": 20,
        "writes_sec": 3.1,
        "reads_sec": 84.2,
        "slow_queries": 0
    }
