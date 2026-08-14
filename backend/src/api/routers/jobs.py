from fastapi import APIRouter, Depends, Query
from typing import Optional
from src.api.dependencies import get_repos
from src.core.repositories.manager import RepositoryManager
from src.runtime.auth.dependencies import get_current_user, CurrentUser

router = APIRouter()

@router.get("")
def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    q: Optional[str] = None,
    status: str = 'ACTIVE',
    min_score: Optional[float] = None,
    location: Optional[str] = None,
    remote_type: Optional[str] = None,
    employment_type: Optional[str] = None,
    seniority: Optional[str] = None,
    min_salary: Optional[float] = None,
    sort_by: str = "score",
    repos: RepositoryManager = Depends(get_repos),
    current_user: CurrentUser = Depends(get_current_user),
):
    return repos.job.get_jobs(
        page=page,
        page_size=page_size,
        provider=provider,
        company=company,
        title=title,
        q=q,
        status=status,
        min_score=min_score,
        # Unified list -- no more ATS-vs-job-board tab split on the
        # dashboard, so this endpoint now returns everything active
        # instead of pipeline "A" (ATS-only). /boards below (pipeline "B")
        # is kept for any caller that still wants the split.
        pipeline="ALL",
        location=location,
        remote_type=remote_type,
        employment_type=employment_type,
        seniority=seniority,
        min_salary=min_salary,
        sort_by=sort_by,
        user_id=current_user.user_id,
    )

@router.get("/title-suggestions")
def get_title_suggestions(
    repos: RepositoryManager = Depends(get_repos),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Distinct active job titles for the frontend's client-side trie --
    instant search-box autocomplete with zero round-trip per keystroke."""
    return {"titles": repos.job.get_title_suggestions()}


@router.get("/boards")
def get_board_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    q: Optional[str] = None,
    status: str = 'ACTIVE',
    min_score: Optional[float] = None,
    location: Optional[str] = None,
    remote_type: Optional[str] = None,
    employment_type: Optional[str] = None,
    seniority: Optional[str] = None,
    min_salary: Optional[float] = None,
    sort_by: str = "newest",
    repos: RepositoryManager = Depends(get_repos),
    current_user: CurrentUser = Depends(get_current_user),
):
    return repos.job.get_jobs(
        page=page,
        page_size=page_size,
        provider=provider,
        company=company,
        title=title,
        q=q,
        status=status,
        min_score=min_score,
        pipeline="B",
        location=location,
        remote_type=remote_type,
        employment_type=employment_type,
        seniority=seniority,
        min_salary=min_salary,
        sort_by=sort_by,
        user_id=current_user.user_id,
    )

@router.get("/{job_id}")
def get_job(job_id: str, repos: RepositoryManager = Depends(get_repos)):
    from fastapi import HTTPException
    job = repos.job.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/sync-history/{company_id}")
def get_sync_history(company_id: str, repos: RepositoryManager = Depends(get_repos)):
    return repos.dashboard.get_job_sync_history(company_id)
