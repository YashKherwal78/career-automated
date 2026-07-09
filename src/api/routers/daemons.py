from fastapi import APIRouter, Depends
import sqlite3
from src.api.dependencies import get_db

router = APIRouter()

@router.get("")
def get_daemons(db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()
    c.row_factory = sqlite3.Row
    c.execute("SELECT * FROM worker_states")
    return [dict(row) for row in c.fetchall()]
