import sqlite3
import time
import json
import uuid
import logging
import os
from enum import Enum
from typing import Dict, Any, Optional
from src.config.settings import settings

logger = logging.getLogger("Telemetry")

class Stage(str, Enum):
    HOMEPAGE_FETCH = "HOMEPAGE_FETCH"
    SEARCH_EXECUTED = "SEARCH_EXECUTED"
    URL_COLLECTED = "URL_COLLECTED"
    URL_DEDUPLICATED = "URL_DEDUPLICATED"
    FINGERPRINT_MATCHED = "FINGERPRINT_MATCHED"
    CANDIDATE_CREATED = "CANDIDATE_CREATED"
    INSPECTOR_EXECUTED = "INSPECTOR_EXECUTED"
    ENDPOINT_PROMOTED = "ENDPOINT_PROMOTED"
    CRAWL_EXECUTED = "CRAWL_EXECUTED"
    NORMALIZATION_EXECUTED = "NORMALIZATION_EXECUTED"

class Status(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"
    RETRY = "RETRY"
    CANCELLED = "CANCELLED"

class ReasonCode(str, Enum):
    NONE = "NONE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    BAD_SSL = "BAD_SSL"
    NO_CAREERS_PAGE = "NO_CAREERS_PAGE"
    INVALID_HTML = "INVALID_HTML"
    UNKNOWN_ATS = "UNKNOWN_ATS"
    PARSER_FAILED = "PARSER_FAILED"
    INSPECTOR_FAILED = "INSPECTOR_FAILED"
    PROMOTION_FAILED = "PROMOTION_FAILED"

class Telemetry:
    TELEMETRY_VERSION = 1
    DB_PATH = settings.db_path

    @staticmethod
    def get_git_commit() -> str:
        try:
            import subprocess
            return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
        except Exception:
            return "unknown"

    @staticmethod
    def get_feature_flags() -> str:
        flags = {k: v for k, v in os.environ.items() if k.startswith("ENABLE_DISCOVERY_") or k.startswith("ENABLE_")}
        # Add settings attributes
        for attr in dir(settings):
            if attr.startswith("enable_"):
                flags[attr.upper()] = getattr(settings, attr)
        return json.dumps(flags)

    @staticmethod
    def start_run(run_id: str, worker: str, trigger: str = "Cron"):
        try:
            now = time.time()
            git_commit = Telemetry.get_git_commit()
            flags = Telemetry.get_feature_flags()
            config_hash = str(hash(flags))
            
            with sqlite3.connect(Telemetry.DB_PATH, timeout=30.0) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO pipeline_runs (
                        run_id, worker, started_at, status, trigger, git_commit, config_hash, feature_flags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (run_id, worker, now, "RUNNING", trigger, git_commit, config_hash, flags))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to start pipeline run: {e}")

    @staticmethod
    def finish_run(run_id: str, status: Status = Status.SUCCESS):
        try:
            now = time.time()
            with sqlite3.connect(Telemetry.DB_PATH, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                # Get start time to compute duration
                cursor = conn.execute("SELECT started_at FROM pipeline_runs WHERE run_id = ?", (run_id,))
                row = cursor.fetchone()
                duration = 0.0
                if row:
                    duration = (now - row["started_at"]) * 1000.0 # ms
                    
                conn.execute("""
                    UPDATE pipeline_runs
                    SET status = ?, finished_at = ?, duration_ms = ?
                    WHERE run_id = ?
                """, (status.value, now, duration, run_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to finish pipeline run: {e}")

    @staticmethod
    def record_event(
        stage: Stage,
        status: Status,
        run_id: str,
        company_id: Optional[str] = None,
        candidate_url: Optional[str] = None,
        worker_name: Optional[str] = None,
        ats_type: Optional[str] = None,
        plugin: Optional[str] = None,
        source: Optional[str] = None,
        latency_ms: Optional[float] = None,
        reason_code: ReasonCode = ReasonCode.NONE,
        parent_event_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        event_id = str(uuid.uuid4())
        # Passengers never drive: Wrap everything in a try-except to never block operations
        try:
            now = time.time()
            meta_str = json.dumps(metadata or {})
            
            with sqlite3.connect(Telemetry.DB_PATH, timeout=30.0) as conn:
                # 1. Insert into Immutable Event Log
                conn.execute("""
                    INSERT INTO pipeline_events (
                        event_id, event_type, payload, timestamp, run_id, company_id, candidate_url,
                        worker_name, stage, status, ats_type, latency_ms, reason_code, parent_event_id, telemetry_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, stage.value, meta_str, now, run_id, company_id, candidate_url,
                    worker_name, stage.value, status.value, ats_type, latency_ms, reason_code.value,
                    parent_event_id, Telemetry.TELEMETRY_VERSION
                ))

                # 2. Update company current trace status
                if company_id:
                    conn.execute("""
                        INSERT INTO company_trace (company_id, run_id, current_stage, current_worker, last_event, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(company_id) DO UPDATE SET
                            run_id = excluded.run_id,
                            current_stage = excluded.current_stage,
                            current_worker = excluded.current_worker,
                            last_event = excluded.last_event,
                            last_updated = excluded.last_updated
                    """, (company_id, run_id, stage.value, worker_name, stage.value, now))

                # 3. Update Pre-Aggregated Metrics

                # Worker Metrics
                if worker_name:
                    latency = latency_ms or 0.0
                    success_val = 1 if status == Status.SUCCESS else 0
                    fail_val = 1 if status == Status.FAILURE else 0
                    conn.execute("""
                        INSERT INTO worker_metrics (timestamp, worker, processed, failed, avg_latency)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(worker) DO UPDATE SET
                            timestamp = excluded.timestamp,
                            processed = processed + excluded.processed,
                            failed = failed + excluded.failed,
                            avg_latency = (avg_latency * 0.9) + (excluded.avg_latency * 0.1)
                    """, (now, worker_name, success_val + fail_val, fail_val, latency))

                # Pipeline Stage Metrics
                latency = latency_ms or 0.0
                success_val = 1 if status == Status.SUCCESS else 0
                fail_val = 1 if status == Status.FAILURE else 0
                conn.execute("""
                    INSERT INTO pipeline_stage_metrics (stage, processed, failed, avg_latency, p95, p99)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(stage) DO UPDATE SET
                        processed = processed + excluded.processed,
                        failed = failed + excluded.failed,
                        avg_latency = (avg_latency * 0.9) + (excluded.avg_latency * 0.1)
                """, (stage.value, success_val + fail_val, fail_val, latency, latency, latency))

                # Plugin Metrics
                if plugin:
                    cand_found = 1 if stage == Stage.CANDIDATE_CREATED else 0
                    ver_found = 1 if stage == Stage.ENDPOINT_PROMOTED else 0
                    conn.execute("""
                        INSERT INTO plugin_metrics (plugin, candidates_found, verified, avg_latency)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(plugin) DO UPDATE SET
                            candidates_found = candidates_found + excluded.candidates_found,
                            verified = verified + excluded.verified,
                            avg_latency = (avg_latency * 0.9) + (excluded.avg_latency * 0.1)
                    """, (plugin, cand_found, ver_found, latency_ms or 0.0))

                # ATS Metrics
                if ats_type:
                    conn.execute("""
                        INSERT INTO ats_metrics (ats_type, companies, latency)
                        VALUES (?, 1, ?)
                        ON CONFLICT(ats_type) DO UPDATE SET
                            companies = companies + 1,
                            latency = (latency * 0.9) + (excluded.latency * 0.1)
                    """, (ats_type, latency_ms or 0.0))

                # Source Metrics
                if source:
                    conn.execute("""
                        INSERT INTO source_metrics (source, urls_produced, avg_latency)
                        VALUES (?, 1, ?)
                        ON CONFLICT(source) DO UPDATE SET
                            urls_produced = urls_produced + 1,
                            avg_latency = (avg_latency * 0.9) + (excluded.avg_latency * 0.1)
                    """, (source, latency_ms or 0.0))

                # 4. Increment pipeline run stats
                if run_id:
                    comp_processed = 1 if stage == Stage.HOMEPAGE_FETCH else 0
                    cand_found = 1 if stage == Stage.CANDIDATE_CREATED else 0
                    verified_found = 1 if stage == Stage.ENDPOINT_PROMOTED else 0
                    jobs_found = 1 if stage == Stage.NORMALIZATION_EXECUTED else 0
                    
                    conn.execute("""
                        UPDATE pipeline_runs
                        SET companies_processed = companies_processed + ?,
                            candidates_found = candidates_found + ?,
                            verified = verified + ?,
                            jobs = jobs + ?
                        WHERE run_id = ?
                    """, (comp_processed, cand_found, verified_found, jobs_found, run_id))

                conn.commit()
        except Exception as e:
            logger.error(f"Telemetry write failure (silently caught): {e}")

        return event_id
