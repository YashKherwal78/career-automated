from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .routers import jobs, companies, applications, contacts, analytics, daemons, settings, activities

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
import sqlite3
import time
from src.config.settings import settings as app_settings
from src.discovery.pipeline.repositories.metrics_repository import MetricsRepository

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

from fastapi.responses import HTMLResponse
import os

@app.get("/mission-control", response_class=HTMLResponse)
def get_mission_control():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "mission_control.html")
    with open(path, "r") as f:
        return f.read()

@app.get("/api/v1/health")
def get_health_status(db: sqlite3.Connection = Depends(get_db)):
    metrics_repo = MetricsRepository(app_settings.db_path)
    metrics = metrics_repo.get_all_metrics()
    
    c = db.cursor()
    c.execute("SELECT count(*) FROM worker_states WHERE status='RUNNING'")
    running_workers = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM ats_registry WHERE status='ACTIVE'")
    active_endpoints = c.fetchone()[0]

    c.execute("SELECT count(*) FROM normalized_jobs WHERE status='ACTIVE'")
    active_jobs = c.fetchone()[0]

    c.execute("SELECT count(*) FROM company_identities")
    total_companies = c.fetchone()[0]

    # Queue counts
    c.execute("SELECT count(*) FROM local_queues WHERE queue_name='discovery_queue' AND status='QUEUED'")
    discovery_depth = c.fetchone()[0]
    c.execute("SELECT count(*) FROM local_queues WHERE queue_name='verification_queue' AND status='QUEUED'")
    verification_depth = c.fetchone()[0]
    c.execute("SELECT count(*) FROM local_queues WHERE queue_name='crawl_queue' AND status='QUEUED'")
    crawl_depth = c.fetchone()[0]
    
    return {
        "status": "healthy" if running_workers > 0 else "degraded",
        "uptime": int(time.time() - start_time),
        "workers": running_workers,
        "database": "healthy",
        "api": "healthy",
        "version": "1.0.0",
        "build": "production",
        "jobs": active_jobs,
        "companies": total_companies,
        "verified": active_endpoints,
        "queues": {
            "discovery_queue": discovery_depth,
            "verification_queue": verification_depth,
            "crawl_queue": crawl_depth
        },
        "metrics": metrics
    }

@app.get("/api/v1/discovery")
def get_discovery_queues(db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()
    # Check if local_queues exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_queues'")
    if not c.fetchone():
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
def get_dashboard_summary(db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()
    
    c.execute("SELECT count(*) FROM company_identities")
    companies = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM ats_registry WHERE status = 'ACTIVE'")
    verified = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM normalized_jobs WHERE status = 'ACTIVE'")
    jobs = c.fetchone()[0]
    
    # Active/failed workers
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_states'")
    if c.fetchone():
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

# Serve the Career Automated Web UI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
