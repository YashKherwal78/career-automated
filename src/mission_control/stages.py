from src.system.logger import setup_logger
logger = setup_logger('stages')
import time
import sqlite3
from typing import Dict, Any, List
from src.mission_control.stage import PipelineStage, PipelineContext

# Import Existing Modules
from src.discovery.providers.provider_manager import ProviderManager
from src.discovery.deduplicator import DiscoveryDeduplicator
from src.discovery.intent_filter import IntentFilter
from src.discovery.hard_reject_filter import HardRejectFilter
from src.discovery.search_planner import SearchTask
from src.intelligence.scoring_engine import JobScoringEngine

class ExtractionStage(PipelineStage):
    @property
    def name(self) -> str: return "Extraction"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        if context.dry_run:
            logger.info("[DRY RUN] Bypassing ProviderManager.")
            return context
            
        logger.info("-> Running ProviderManager (Pipeline 1 & 2)")
        manager = ProviderManager()
        # Ensure we return dictionaries for the next stage
        raw_jobs = manager.run_all_providers()
        context.raw_jobs = [j if isinstance(j, dict) else j.to_dict() for j in raw_jobs]
        context.metrics["jobs_extracted"] = len(context.raw_jobs)
        return context

class DeduplicationStage(PipelineStage):
    @property
    def name(self) -> str: return "Deduplication"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info("-> Running DiscoveryDeduplicator")
        deduper = DiscoveryDeduplicator()
        context.deduplicated_jobs = deduper.deduplicate(context.raw_jobs)
        context.metrics["jobs_deduplicated"] = len(context.raw_jobs) - len(context.deduplicated_jobs)
        return context

class IntentStage(PipelineStage):
    @property
    def name(self) -> str: return "Intent Filter (Seniority & Role)"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info("-> Running IntentFilter")
        filter_engine = IntentFilter()
        # Mock SearchTask config
        task = SearchTask(
            connector="all",
            role_family="AI Engineer",
            canonical_query="AI",
            locations=["remote", "india"],
            experience_profile=["Entry", "Associate"], # Explicitly drop Seniors
            employment_types=["Full-time"],
            work_modes=["Remote"],
            freshness_days=7,
            budget={"max_queries": 1, "max_results": 50}
        )
        
        passed, rejected, metrics = filter_engine.filter_opportunities(context.deduplicated_jobs, task)
        context.intent_passed_jobs = passed
        context.metrics["jobs_intent_rejected"] = metrics.get("jobs_rejected_experience", 0) + metrics.get("jobs_rejected_role", 0)
        return context


class HardRejectStage(PipelineStage):
    @property
    def name(self) -> str: return "Hard Reject Filter"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info("-> Running HardRejectFilter")
        filter_engine = HardRejectFilter()
        # Mock SearchTask config; in reality, load from platform.yaml
        task = SearchTask(
            connector="all",
            role_family="AI Engineer",
            canonical_query="AI",
            locations=["remote", "india"],
            experience_profile=["Full-Time"],
            employment_types=["Full-time"],
            work_modes=["Remote"],
            freshness_days=7,
            budget={"max_queries": 1, "max_results": 50}
        )
        
        passed, rejected, metrics = filter_engine.filter_opportunities(getattr(context, 'intent_passed_jobs', context.deduplicated_jobs), task)
        context.passed_jobs = passed
        context.metrics["jobs_rejected"] = metrics.get("jobs_hard_rejected", len(rejected))
        return context

class PersistenceStage(PipelineStage):
    @property
    def name(self) -> str: return "Job Repository (normalized_jobs)"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        if context.dry_run:
            logger.info("[DRY RUN] Bypassing SQLite save.")
            return context
            
        logger.info("-> Saving to normalized_jobs")
        # In a real implementation, this would upsert to data/crm.db
        return context

class ScoringStage(PipelineStage):
    @property
    def name(self) -> str: return "Job Scoring Engine"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        if context.dry_run:
            logger.info("[DRY RUN] Bypassing JobScoringEngine.")
            return context
            
        logger.info("-> Running JobScoringEngine")
        # Instantiate and run existing scoring engine
        engine = JobScoringEngine(db_path="data/crm.db")
        engine.score_active_jobs()
        context.metrics["jobs_scored"] = len(context.passed_jobs)
        return context

class ResumeTailorStage(PipelineStage):
    @property
    def name(self) -> str: return "Resume Tailoring"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info("-> Running agent5_resume_tailor (Mock)")
        if not context.dry_run:
            pass # Hook to agent5
        context.metrics["resumes_tailored"] = 0
        return context

class ContactDiscoveryStage(PipelineStage):
    @property
    def name(self) -> str: return "Contact Discovery"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info("-> Running Contact Discovery (Mock)")
        context.metrics["contacts_found"] = 0
        return context

class StrategyQueueStage(PipelineStage):
    @property
    def name(self) -> str: return "Application Strategy Queue"
    
    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info("-> Populating Strategy Queue (Mock)")
        context.metrics["strategy_queue_size"] = context.metrics["jobs_scored"]
        return context
