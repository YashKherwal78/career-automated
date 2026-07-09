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
