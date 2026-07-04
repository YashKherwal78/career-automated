from fastapi import APIRouter, Depends, Query
import sqlite3
from typing import Optional
from src.api.dependencies import get_db
from src.api.repositories.jobs_repository import JobRepository

router = APIRouter()

def get_job_repo(db: sqlite3.Connection = Depends(get_db)):
    return JobRepository(db)

@router.get("")
def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    company: Optional[str] = None,
    status: str = 'ACTIVE',
    min_score: Optional[float] = None,
    repo: JobRepository = Depends(get_job_repo)
):
    return repo.get_jobs(page, page_size, provider, company, status, min_score)
