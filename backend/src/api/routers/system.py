from fastapi import APIRouter, Depends
from src.api.dependencies import get_repos

router = APIRouter()

@router.get("/repositories")
def get_repository_health(repos = Depends(get_repos)):
    """Check health of all repository instances."""
    return {
        "company": "healthy" if repos.company else "error",
        "company_state": "healthy" if repos.company_state else "error",
        "worker": "healthy" if repos.worker else "error",
        "session": "healthy" if repos.session else "error",
        "provider": "healthy" if repos.provider else "error",
        "job": "healthy" if repos.job else "error",
        "migration": "healthy" if repos.migration else "error",
        "scheduler": "healthy" if repos.scheduler else "error",
    }

@router.get("/version")
def get_version(repos = Depends(get_repos)):
    """Return API version and DB details."""
    from src.api.db import is_postgres
    schema_version = "unknown"
    try:
        with repos.transaction() as conn:
            cur = conn.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                schema_version = row[0]
    except Exception:
        pass

    return {
        "api_version": "v1",
        "schema_version": schema_version,
        "database": "postgres" if is_postgres() else "sqlite",
        "environment": "development", # Hardcoded for now
        "build": "abc123" # Mock build ID
    }
