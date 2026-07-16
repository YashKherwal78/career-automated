from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.get("")
def list_workers(repos = Depends(get_repos)):
    return {"workers": repos.worker.get_workers()}
