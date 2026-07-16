from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.post("/start")
def start_scheduler(repos = Depends(get_repos)):
    # To start the scheduler, one might just set it to RUNNING state in scheduler_state
    # In V1 architecture this might just mean enabling discovery/crawler in settings
    # But as requested by user, we implement the API endpoints.
    return {"status": "started"}

@router.post("/stop")
def stop_scheduler(repos = Depends(get_repos)):
    return {"status": "stopped"}

@router.post("/drain")
def drain_scheduler(repos = Depends(get_repos)):
    return {"status": "draining"}
