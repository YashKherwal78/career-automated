import os
from dataclasses import dataclass, field

@dataclass
class Settings:
    db_path: str = os.environ.get("DATABASE_PATH", "data/crm.db")

    # ── Pipeline-level flags ────────────────────────────────────────────────
    # ENABLE_PIPELINE_A: Company Seed → ATS Discovery → Connector → Jobs
    # ENABLE_PIPELINE_B: Job Boards (LinkedIn, Google Jobs, etc.) → Jobs
    enable_pipeline_a: bool = os.environ.get("ENABLE_PIPELINE_A", "True").lower() == "true"
    enable_pipeline_b: bool = os.environ.get("ENABLE_PIPELINE_B", "True").lower() == "true"

    # ── Pipeline A worker flags (respected independently) ───────────────────
    # Feature Flags
    enable_discovery: bool = os.environ.get("ENABLE_DISCOVERY", "True").lower() == "true"
    enable_verification: bool = os.environ.get("ENABLE_VERIFICATION", "True").lower() == "true"
    enable_crawler: bool = os.environ.get("ENABLE_CRAWLER", "True").lower() == "true"
    enable_ranking: bool = os.environ.get("ENABLE_RANKING", "True").lower() == "true"
    enable_cleanup: bool = os.environ.get("ENABLE_CLEANUP", "True").lower() == "true"

    # Discovery Plugin Rollout Flags
    enable_discovery_plugin_ashby: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_ASHBY", "True").lower() == "true"
    enable_discovery_plugin_workable: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_WORKABLE", "True").lower() == "true"
    enable_discovery_plugin_smartrecruiters: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_SMARTRECRUITERS", "True").lower() == "true"
    enable_discovery_plugin_teamtailor: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_TEAMTAILOR", "True").lower() == "true"
    enable_discovery_plugin_breezy: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_BREEZY", "True").lower() == "true"
    enable_discovery_plugin_recruitee: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_RECRUITEE", "True").lower() == "true"
    enable_discovery_plugin_jobvite: bool = os.environ.get("ENABLE_DISCOVERY_PLUGIN_JOBVITE", "True").lower() == "true"

    # Worker Timing Intervals (in seconds)
    discovery_interval: int = int(os.environ.get("DISCOVERY_INTERVAL", "900"))       # 15 mins
    verification_interval: int = int(os.environ.get("VERIFICATION_INTERVAL", "300")) # 5 mins
    crawler_interval: int = int(os.environ.get("CRAWLER_INTERVAL", "120"))           # 2 mins
    cleanup_interval: int = int(os.environ.get("CLEANUP_INTERVAL", "3600"))          # 1 hour

    # Crawler Poll Interval (when queue/jobs are empty, how long to sleep)
    crawler_poll_interval: int = int(os.environ.get("CRAWLER_POLL_INTERVAL", "30"))

    # Pipeline B interval: how often JobBoardWorker runs a full provider sweep
    pipeline_b_interval: int = int(os.environ.get("PIPELINE_B_INTERVAL", "3600"))  # 1 hour

    # Failures backoff schedule
    retry_schedule: list = field(default_factory=lambda: [300, 900, 1800, 3600, 21600, 86400])

# Global Singleton
settings = Settings()
