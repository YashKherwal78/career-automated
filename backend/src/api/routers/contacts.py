from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.get("/")
def get_contacts(repos = Depends(get_repos)):
    return {"message": "Welcome to contacts API"}
