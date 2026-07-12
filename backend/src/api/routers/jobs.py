from fastapi import APIRouter, Depends, Query
from typing import Optional
from src.api.dependencies import get_db
from src.api.repositories.jobs_repository import JobRepository

router = APIRouter()

def get_job_repo(db = Depends(get_db)):
    return JobRepository(db)

@router.get("")
def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    company: Optional[str] = None,
    status: str = 'ACTIVE',
    min_score: Optional[float] = None,
    location: Optional[str] = None,
    remote_type: Optional[str] = None,
    employment_type: Optional[str] = None,
    seniority: Optional[str] = None,
    min_salary: Optional[float] = None,
    sort_by: str = "score",
    repo: JobRepository = Depends(get_job_repo)
):
    return repo.get_jobs(
        page=page,
        page_size=page_size,
        provider=provider,
        company=company,
        status=status,
        min_score=min_score,
        pipeline="A",
        location=location,
        remote_type=remote_type,
        employment_type=employment_type,
        seniority=seniority,
        min_salary=min_salary,
        sort_by=sort_by
    )

@router.get("/boards")
def get_board_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    company: Optional[str] = None,
    status: str = 'ACTIVE',
    min_score: Optional[float] = None,
    location: Optional[str] = None,
    remote_type: Optional[str] = None,
    employment_type: Optional[str] = None,
    seniority: Optional[str] = None,
    min_salary: Optional[float] = None,
    sort_by: str = "newest",
    repo: JobRepository = Depends(get_job_repo)
):
    return repo.get_jobs(
        page=page,
        page_size=page_size,
        provider=provider,
        company=company,
        status=status,
        min_score=min_score,
        pipeline="B",
        location=location,
        remote_type=remote_type,
        employment_type=employment_type,
        seniority=seniority,
        min_salary=min_salary,
        sort_by=sort_by
    )

@router.get("/{job_id}")
def get_job(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    from fastapi import HTTPException
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
