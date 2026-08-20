from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from typing import Optional
from src.api.dependencies import get_repos
from src.core.repositories.manager import RepositoryManager
from src.runtime.auth.dependencies import get_current_user, CurrentUser

router = APIRouter()


@router.post("/upload-screenshot")
def upload_job_screenshot(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a screenshot of a job post (a LinkedIn post, a tweet, anything
    with a role/company/apply-info visible) and get back the company, role,
    location, and apply link the vision model pulled out of it -- the same
    extraction the screenshot-batch CLI pipeline uses
    (src.ingestion.screenshot_extractor.extract_from_image), just triggered
    from the dashboard instead of a folder of files on disk.

    Deliberately extraction-only: this does not enrich the JD, route to a
    connector, or apply. It answers "what did we read off this image" so
    the candidate can see the upload actually worked; applying is a
    separate, explicit action elsewhere in the product."""
    import os
    import tempfile
    import uuid

    ext = os.path.splitext(file.filename or "")[1].lower()
    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PNG, JPG, and WEBP screenshots are supported. Got: {ext or 'unknown'}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        import shutil
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        from src.ingestion.screenshot_extractor import extract_from_image
        from src.ingestion.job_lead import JobLead
        from src.ingestion.jd_enrichment import record_lead

        lead: Optional[JobLead] = extract_from_image(tmp_path)
        run_id = f"upload_{uuid.uuid4().hex[:12]}"

        if lead is None:
            return {
                "success": False,
                "message": "Couldn't read a job posting out of that screenshot -- try a clearer or fuller screenshot of the post.",
            }

        record_lead(
            lead, user_id=current_user.user_id, connector="", jd_source="none",
            result_status="EXTRACTED_ONLY", really_submitted=False, execution_run_id=run_id,
        )

        return {
            "success": True,
            "company": lead.company,
            "role": lead.role,
            "apply_link": lead.apply_link,
            "location": lead.location,
            "jd_excerpt": lead.jd_excerpt,
        }
    finally:
        os.unlink(tmp_path)

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
    max_salary: Optional[float] = None,
    posted_within_days: Optional[int] = None,
    sort_by: str = "score",
    max_experience_years: Optional[float] = None,
    include_interns: bool = True,
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
        max_salary=max_salary,
        posted_within_days=posted_within_days,
        sort_by=sort_by,
        max_experience_years=max_experience_years,
        include_interns=include_interns,
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
    max_experience_years: Optional[float] = None,
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
        max_experience_years=max_experience_years,
        user_id=current_user.user_id,
    )

@router.get("/semantic-search")
def semantic_search_jobs(
    k: int = Query(50, ge=1, le=500),
    max_experience_years: Optional[float] = None,
    repos: RepositoryManager = Depends(get_repos),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Ranks jobs purely by embedding cosine similarity to this candidate's
    profile embedding (user_career_profiles.embedding), across the entire
    ACTIVE pool -- not the recency-bounded window /jobs uses. No keyword/
    rule filtering applied EXCEPT max_experience_years, which is a real SQL
    WHERE clause (see get_jobs_by_vector_similarity's docstring for why
    this can't be a similarity/embedding thing -- a hard cutoff needs a
    hard filter, not a nudge in vector space). Each result carries
    vector_similarity (0-1, higher = closer) so callers/UI can show or
    threshold on it. Returns an empty list (not an error) if the candidate
    has no profile embedding yet -- store_candidate_embedding runs on
    profile save."""
    return {
        "jobs": repos.job.get_jobs_by_vector_similarity(
            current_user.user_id, k=k, max_experience_years=max_experience_years
        )
    }


@router.get("/hybrid-search")
def hybrid_search_jobs(
    k: int = Query(50, ge=1, le=500),
    max_experience_years: Optional[float] = None,
    embedding_version: str = Query("v1", pattern="^(v1|v2)$"),
    repos: RepositoryManager = Depends(get_repos),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Reciprocal rank fusion of vector similarity + BM25-style full-text
    search (normalized_jobs.search_vector, migration 044) -- recovers
    exact/rare-term matches (a specific tool, framework, certification)
    that pure semantic similarity blurs into a general topical
    neighborhood, same reasoning the RAG system's hybrid retrieval
    already uses. Each result carries both rrf_score and vector_similarity
    so callers/UI can show either. Returns an empty list (not an error) if
    the candidate has no profile embedding yet.

    embedding_version="v2" opts into embedding_v2 (nomic-embed-text-v1.5,
    768-dim, 8192-token context, migration 045) instead of the live
    bge-small `embedding` column -- see get_jobs_by_hybrid_search_v2's
    docstring. Explicit opt-in, not the default: the v2 backfill is still
    in progress and its HNSW index must exist before calling this at any
    real traffic volume (see CLAUDE.md)."""
    if embedding_version == "v2":
        jobs = repos.job.get_jobs_by_hybrid_search_v2(
            current_user.user_id, k=k, max_experience_years=max_experience_years
        )
    else:
        jobs = repos.job.get_jobs_by_hybrid_search(
            current_user.user_id, k=k, max_experience_years=max_experience_years
        )
    return {"jobs": jobs}


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
