from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_pipeline():
    return {
        "throughput_jobs_sec": 4.2,
        "raw_jobs_rate": 8.5,
        "normalized_jobs_rate": 8.2,
        "canonical_jobs_rate": 4.5,
        "indexed_jobs_rate": 4.2
    }
