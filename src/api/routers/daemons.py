from fastapi import APIRouter, Depends
import sqlite3
from src.api.dependencies import get_db

router = APIRouter()

@router.get("/")
def get_daemons(db: sqlite3.Connection = Depends(get_db)):
    return {"message": "Welcome to daemons API"}
