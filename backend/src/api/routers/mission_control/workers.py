from fastapi import APIRouter
from src.runtime.postgres.connection import get_connection

router = APIRouter()

@router.get("")
def get_workers():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT worker_id, worker_name, worker_type, pid, status, cpu_percent, memory_mb, current_task FROM public.worker_states")
            rows = cursor.fetchall()
            workers = [{
                "id": r[0], "name": r[1], "type": r[2], "pid": r[3], "status": r[4], "cpu": r[5], "ram": r[6], "current_task": r[7]
            } for r in rows]
    except Exception:
        workers = []
    return workers
