from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.post("/{provider_id}/enable")
def enable_provider(provider_id: str, repos = Depends(get_repos)):
    repos.provider.enable_provider(provider_id)
    return {"status": "enabled"}

@router.post("/{provider_id}/disable")
def disable_provider(provider_id: str, repos = Depends(get_repos)):
    repos.provider.disable_provider(provider_id)
    return {"status": "disabled"}
