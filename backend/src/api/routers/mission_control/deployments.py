from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_deployments():
    return {
        "git_commit": "30dbf13",
        "branch": "v2",
        "environment": "Production",
        "uptime_days": 12.4
    }
