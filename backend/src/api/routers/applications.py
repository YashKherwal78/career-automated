from fastapi import APIRouter, Depends
from src.api.dependencies import get_db

router = APIRouter()

@router.get("/")
def get_applications(db = Depends(get_db)):
    return {"message": "Welcome to applications API"}
