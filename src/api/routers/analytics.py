from fastapi import APIRouter, Depends
import sqlite3
from src.api.dependencies import get_db
from src.api.repositories.analytics_repository import AnalyticsRepository

router = APIRouter()

def get_analytics_repo(db: sqlite3.Connection = Depends(get_db)):
    return AnalyticsRepository(db)

@router.get("/funnel")
def get_funnel(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_funnel_kpis()

@router.get("/pipeline")
def get_pipeline(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_pipeline_kpis()

@router.get("/runs")
def get_runs(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_runs()

@router.get("/plugins")
def get_plugins(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_plugins()

@router.get("/sources")
def get_sources(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_sources()

@router.get("/workers")
def get_workers(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_workers()

@router.get("/queues")
def get_queues(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_queues()

@router.get("/data-quality")
def get_data_quality(repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_data_quality()

@router.get("/lineage/{company_id}")
def get_lineage(company_id: str, repo: AnalyticsRepository = Depends(get_analytics_repo)):
    return repo.get_lineage(company_id)
