from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_repos
from src.core.repositories.manager import RepositoryManager
from src.applications.apply_service import apply_to_job

router = APIRouter()

@router.get("/")
def get_applications(repos = Depends(get_repos)):
    return {"message": "Welcome to applications API"}


class ApplyRequest(BaseModel):
    # Defaults to True (never clicks final submit) — the same safe default
    # as ApplicationDispatcher.dispatch() itself. A real submission requires
    # the caller to explicitly opt in.
    test_mode: bool = True


@router.post("/{job_id}/apply")
def apply_to_job_endpoint(
    job_id: str,
    body: ApplyRequest = ApplyRequest(),
    repos: RepositoryManager = Depends(get_repos),
):
    job_row = repos.job.get_job(job_id)
    if not job_row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    result = apply_to_job(job_row, test_mode=body.test_mode)
    return {
        "status": result.status,
        # The only field that answers "was this actually submitted?" — a
        # dry run (test_mode=True) can reach status="COMPLETED" too, without
        # ever clicking submit, so status alone is not proof of submission.
        "really_submitted": result.really_submitted,
        "confirmation_url": result.confirmation_url,
        "screenshot_path": result.screenshot_path,
        "submitted_answers": result.submitted_answers,
        "failure_reason": result.failure_reason,
    }
