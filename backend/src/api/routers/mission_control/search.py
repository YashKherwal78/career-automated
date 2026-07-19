from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_search():
    return {
        "status": "Not Yet Instrumented",
        "description": "Index metrics and search CTR logs are not instrumented."
    }
