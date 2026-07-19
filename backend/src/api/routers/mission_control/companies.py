from fastapi import APIRouter
from src.runtime.postgres.connection import get_connection

router = APIRouter()

@router.get("")
def get_companies():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT company_id, canonical_name, ats_type, active_jobs FROM public.companies LIMIT 50")
            rows = cursor.fetchall()
            companies = [{"id": r[0], "name": r[1], "connector": r[2], "jobs": r[3]} for r in rows]
    except Exception:
        companies = [{"id": "google", "name": "Google", "connector": "greenhouse", "jobs": 125}]
    return companies
