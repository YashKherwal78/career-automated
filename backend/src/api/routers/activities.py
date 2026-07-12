from fastapi import APIRouter, Depends
from src.api.dependencies import get_db

router = APIRouter()

@router.get("/")
def get_activities(db = Depends(get_db)):
    return {"message": "Welcome to activities API"}
