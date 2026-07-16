from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.get("")
def get_companies(
    page: int = 1,
    page_size: int = 50,
    repos = Depends(get_repos)
):
    return repos.company.get_companies(page=page, page_size=page_size)
