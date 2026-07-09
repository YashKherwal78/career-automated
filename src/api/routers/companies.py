from fastapi import APIRouter, Depends
import sqlite3
from src.api.dependencies import get_db

router = APIRouter()

@router.get("")
def get_companies(
    page: int = 1,
    page_size: int = 50,
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.row_factory = sqlite3.Row
    c.execute("""
        SELECT 
            i.company_id, 
            i.canonical_name as company_name, 
            i.website, 
            r.ats_type, 
            r.status,
            r.job_count, 
            r.last_checked, 
            r.crawl_status
        FROM company_identities i
        LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
        LIMIT ? OFFSET ?
    """, (page_size, (page - 1) * page_size))
    return [dict(row) for row in c.fetchall()]
