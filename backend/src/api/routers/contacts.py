from fastapi import APIRouter, Depends
from src.api.dependencies import get_db

router = APIRouter()

@router.get("/")
def get_contacts(db = Depends(get_db)):
    return {"message": "Welcome to contacts API"}
