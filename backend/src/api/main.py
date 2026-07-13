from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .routers import jobs, companies, applications, contacts, analytics, daemons, settings, activities, health

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

app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(daemons.router, prefix="/api/v1/daemons", tags=["Daemons"])
app.include_router(daemons.router, prefix="/api/v1/workers", tags=["Workers"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(activities.router, prefix="/api/v1/activities", tags=["Activities"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

from fastapi.responses import HTMLResponse
import os
from pathlib import Path

# The React application is deployed independently.  A static build can still be
# served by setting FRONTEND_STATIC_DIR to a directory that exists at runtime.


@app.get("/api/v1/discovery")
def get_discovery_queues(db = Depends(get_db)):
    c = db.cursor()
    # Check if local_queues exists
    if not table_exists(db, "local_queues"):
        return {"discovery_queue": 0, "verification_queue": 0, "crawl_queue": 0}
        
    c.execute("SELECT count(*) FROM local_queues WHERE queue_name = 'discovery_queue' AND status = 'QUEUED'")
    dq = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM local_queues WHERE queue_name = 'verification_queue' AND status = 'QUEUED'")
    vq = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM local_queues WHERE queue_name = 'crawl_queue' AND status = 'QUEUED'")
    cq = c.fetchone()[0]
    
    return {
        "discovery_queue": dq,
        "verification_queue": vq,
        "crawl_queue": cq
    }

@app.get("/api/v1/dashboard")
def get_dashboard_summary(db = Depends(get_db)):
    c = db.cursor()
    
    c.execute("SELECT count(*) FROM company_identities")
    companies = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM ats_registry WHERE status = 'ACTIVE'")
    verified = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM normalized_jobs WHERE status = 'ACTIVE'")
    jobs = c.fetchone()[0]
    
    # Active/failed workers
    if table_exists(db, "worker_states"):
        c.execute("SELECT count(*) FROM worker_states WHERE status = 'RUNNING'")
        active_w = c.fetchone()[0]
        c.execute("SELECT count(*) FROM worker_states WHERE failures > 0")
        failed_w = c.fetchone()[0]
    else:
        active_w = 0
        failed_w = 0
        
    # Queue counts
    q_counts = get_discovery_queues(db)
    
    return {
        "companies": companies,
        "verified": verified,
        "jobs": jobs,
        "active_workers": active_w,
        "failed_workers": failed_w,
        "discovery_queue": q_counts["discovery_queue"],
        "verification_queue": q_counts["verification_queue"],
        "crawl_queue": q_counts["crawl_queue"]
    }

frontend_static_dir = os.environ.get("FRONTEND_STATIC_DIR")
if frontend_static_dir and Path(frontend_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=frontend_static_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
