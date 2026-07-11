import os
import sys

# Ensure absolute imports work when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import argparse
import time
import uuid
import json

from src.system.logger import setup_logger
from src.system.health_check import run_health_check
from src.system.integration_registry import print_registry
from src.crm.db_init import init_db
from src.mission_control.stage import PipelineContext
from src.mission_control.stages import (
    ExtractionStage, DeduplicationStage, IntentStage, HardRejectStage,
    PersistenceStage, ScoringStage, ResumeTailorStage,
    ContactDiscoveryStage, StrategyQueueStage
)

logger = setup_logger("PipelineOrchestrator")

def build_pipeline():
    return [
        ExtractionStage(),
        DeduplicationStage(),
        IntentStage(),
        HardRejectStage(),
        PersistenceStage(),
        ScoringStage(),
        ResumeTailorStage(),
        ContactDiscoveryStage(),
        StrategyQueueStage()
    ]

def run(dry_run: bool = False):
    logger.info("========== STARTING CAREER AUTOMATED BOOT SEQUENCE ==========")
    
    # 1. Load Config (Implicit via imports, but we can log it)
    logger.info("[1/8] Loading Configuration...")
    
    # 2. Initialize Logger
    logger.info("[2/8] Initializing Logger...")
    
    # 3. Health Check
    logger.info("[3/8] Running System Health Check...")
    run_health_check()
    
    # 4. Integration Registry
    logger.info("[4/8] Loading Integration Registry...")
    print_registry()
    
    # 5. Database Migration / Init
    logger.info("[5/8] Validating Database Schema & Migrations...")
    if not dry_run:
        init_db()
        
    # 6. Load Candidate Context
    logger.info("[6/8] Loading Candidate Context...")
    # TODO: Load Candidate Context Logic
    
    # 7. Initialize Services
    logger.info("[7/8] Initializing Pipeline Services...")
    context = PipelineContext(run_id=str(uuid.uuid4()), dry_run=dry_run)
    pipeline = build_pipeline()
    
    # 8. Scheduler / Pipeline Run
    logger.info(f"[8/8] Pipeline Ready. Starting execution (Dry Run: {dry_run})")
    
    for stage in pipeline:
        start_time = time.time()
        try:
            logger.info(f"[{stage.name}] Starting...")
            context = stage.run(context)
            
            elapsed = time.time() - start_time
            context.metrics["stage_times"][stage.name] = round(elapsed, 2)
            logger.info(f"[{stage.name}] Completed in {elapsed:.2f}s")
            
            # Simulated Checkpoint Save
            # if not dry_run: save_checkpoint(context)
            
        except Exception as e:
            logger.error(f"[{stage.name}] ERROR: {str(e)}")
            context.metrics["errors"] += 1
            break # Halt pipeline on critical failure
            
    logger.info("\n========== PIPELINE COMPLETE ==========")
    logger.info("Metrics Report:")
    logger.info("\n" + json.dumps(context.metrics, indent=2))
    
    # In a full run, we would push these metrics to the SQLite db for Streamlit to consume
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without mutating the database")
    args = parser.parse_args()
    
    run(dry_run=args.dry_run)
