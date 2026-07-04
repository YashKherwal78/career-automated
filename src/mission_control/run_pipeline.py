import argparse
import time
import uuid
import json
from src.mission_control.stage import PipelineContext
from src.mission_control.stages import (
    ExtractionStage, DeduplicationStage, IntentStage, HardRejectStage,
    PersistenceStage, ScoringStage, ResumeTailorStage,
    ContactDiscoveryStage, StrategyQueueStage
)

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
    context = PipelineContext(run_id=str(uuid.uuid4()), dry_run=dry_run)
    pipeline = build_pipeline()
    
    print(f"========== STARTING INTEGRATION PIPELINE (Dry Run: {dry_run}) ==========")
    
    for stage in pipeline:
        start_time = time.time()
        try:
            print(f"[{stage.name}] Starting...")
            context = stage.run(context)
            
            elapsed = time.time() - start_time
            context.metrics["stage_times"][stage.name] = round(elapsed, 2)
            print(f"[{stage.name}] Completed in {elapsed:.2f}s")
            
            # Simulated Checkpoint Save
            # if not dry_run: save_checkpoint(context)
            
        except Exception as e:
            print(f"[{stage.name}] ERROR: {str(e)}")
            context.metrics["errors"] += 1
            break # Halt pipeline on critical failure
            
    print("\n========== PIPELINE COMPLETE ==========")
    print("Metrics Report:")
    print(json.dumps(context.metrics, indent=2))
    
    # In a full run, we would push these metrics to the SQLite db for Streamlit to consume
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without mutating the database")
    args = parser.parse_args()
    
    run(dry_run=args.dry_run)
