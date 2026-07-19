from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_queues():
    return {
        "seed_queue": {"depth": 14, "status": "HEALTHY"},
        "company_queue": {"depth": 48, "status": "HEALTHY"},
        "verification_queue": {"depth": 5, "status": "HEALTHY"},
        "crawler_queue": {"depth": 102, "status": "HEALTHY"},
        "embedding_queue": {"depth": 0, "status": "HEALTHY"},
        "dead_letter_queue": {"depth": 0, "status": "HEALTHY"}
    }
