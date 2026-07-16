from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .routers import jobs, companies, applications, contacts, analytics, daemons, settings, activities, health, system, scheduler, providers, users
from src.runtime.auth.dependencies import get_current_user

app = FastAPI(title="Career Automated API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from src.api.dependencies import get_db
import time
from src.api.db import table_exists, DATABASE_URL, USE_POSTGRES
from src.config.settings import settings as app_settings
from src.discovery.pipeline.repositories.metrics_repository import MetricsRepository
import logging

logger = logging.getLogger("startup")
logger.setLevel(logging.INFO)
logger.info(f"STARTUP DATABASE_URL: {bool(DATABASE_URL)} USE_POSTGRES: {USE_POSTGRES}")

start_time = time.time()

# Authenticated Routers
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"], dependencies=[Depends(get_current_user)])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"], dependencies=[Depends(get_current_user)])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"], dependencies=[Depends(get_current_user)])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"], dependencies=[Depends(get_current_user)])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"], dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"], dependencies=[Depends(get_current_user)])
app.include_router(daemons.router, prefix="/api/v1/daemons", tags=["Daemons"], dependencies=[Depends(get_current_user)])
app.include_router(daemons.router, prefix="/api/v1/workers", tags=["Workers"], dependencies=[Depends(get_current_user)])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"], dependencies=[Depends(get_current_user)])
app.include_router(activities.router, prefix="/api/v1/activities", tags=["Activities"], dependencies=[Depends(get_current_user)])
app.include_router(system.router, prefix="/api/v1/system", tags=["System"], dependencies=[Depends(get_current_user)])
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["Scheduler"], dependencies=[Depends(get_current_user)])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["Providers"], dependencies=[Depends(get_current_user)])

# Public Routers
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

from fastapi.responses import HTMLResponse
import os
from pathlib import Path

# The React application is deployed independently.  A static build can still be
# served by setting FRONTEND_STATIC_DIR to a directory that exists at runtime.


from src.api.dependencies import get_repos

@app.get("/api/v1/discovery")
def get_discovery_queues(repos = Depends(get_repos), current_user = Depends(get_current_user)):
    return repos.dashboard.get_queue_counts()

@app.get("/api/v1/dashboard")
def get_dashboard_summary(repos = Depends(get_repos), current_user = Depends(get_current_user)):
    metrics = repos.dashboard.get_pipeline_metrics()
    funnel = metrics.get("funnel", {})
    workers = metrics.get("workers", [])
    
    active_w = sum(1 for w in workers if w.get("status") == "RUNNING")
    failed_w = sum(1 for w in workers if w.get("failures", 0) > 0)
    
    q_counts = repos.dashboard.get_queue_counts()
    
    return {
        "companies": funnel.get("companies_discovered", 0),
        "verified": funnel.get("ats_registry_active", 0),
        "jobs": funnel.get("jobs_active", 0),
        "active_workers": active_w,
        "failed_workers": failed_w,
        "discovery_queue": q_counts.get("discovery_queue", 0),
        "verification_queue": q_counts.get("verification_queue", 0),
        "crawl_queue": q_counts.get("crawl_queue", 0)
    }

frontend_static_dir = os.environ.get("FRONTEND_STATIC_DIR")
if frontend_static_dir and Path(frontend_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=frontend_static_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
