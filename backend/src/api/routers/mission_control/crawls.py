from fastapi import APIRouter
from src.runtime.postgres.connection import get_connection

router = APIRouter()

@router.get("")
def get_crawls():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, provider, status, started_at, ended_at, jobs_found FROM public.crawl_sessions ORDER BY started_at DESC LIMIT 20")
            rows = cursor.fetchall()
            crawls = [{
                "id": r[0], "provider": r[1], "status": r[2], "started": str(r[3]), "ended": str(r[4]) if r[4] else None, "jobs": r[5]
            } for r in rows]
    except Exception:
        crawls = []
    return crawls
