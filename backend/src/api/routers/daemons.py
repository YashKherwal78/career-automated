from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies import get_repos

router = APIRouter()

@router.get("")
def get_daemons(repos = Depends(get_repos)):
    return repos.worker.get_workers()

@router.get("/{worker_id}")
def get_worker(worker_id: str, repos = Depends(get_repos)):
    worker = repos.worker.get_worker_state(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker
