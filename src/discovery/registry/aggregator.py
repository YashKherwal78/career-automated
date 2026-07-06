from src.system.logger import setup_logger
logger = setup_logger('aggregator')
import sqlite3
import datetime
import uuid
import time
from typing import List, Dict, Any, Type
from abc import ABC, abstractmethod

class SourceConnector(ABC):
    source_name: str
    priority: int
    refresh_interval: str
    version: str = "1.0.0"
    supports_resume: bool = False
    supports_incremental: bool = False
    supports_api: bool = False
    supports_pagination: bool = False
    estimated_company_count: int = 0
    
    @abstractmethod
    def discover_companies(self) -> List[Dict[str, Any]]:
        pass

class SourceConnectorRegistry:
    _registry: Dict[str, Type[SourceConnector]] = {}
    
    @classmethod
    def register(cls, connector_cls: Type[SourceConnector]):
        cls._registry[connector_cls.__name__] = connector_cls
        
    @classmethod
    def get_all(cls) -> Dict[str, Type[SourceConnector]]:
        return cls._registry

class SourceAggregator:
    def __init__(self, db_path: str, config: dict = None):
        self.db_path = db_path
        if config is None:
            import yaml, os
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "crawl_config.yaml")
            try:
                with open(config_path, "r") as f:
                    self.config = yaml.safe_load(f)
            except Exception:
                self.config = {}
        else:
            self.config = config
            
        self.active_connectors: List[SourceConnector] = []
        self._initialize_connectors()

    def _initialize_connectors(self):
        connector_config = self.config.get("connectors", {})
        for name, cls in SourceConnectorRegistry.get_all().items():
            config_key = name.lower().replace("connector", "")
            if config_key == "yc": config_key = "y_combinator"
            if config_key == "peakxv": config_key = "peak_xv"
            if config_key == "techcrunchrss": config_key = "techcrunch_rss"
            
            if connector_config.get(config_key, {}).get("enabled", True):
                self.active_connectors.append(cls(self.db_path))

    def log_crawl_run(self, connector_name: str, started_at: str, stats: dict, status: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        run_id = str(uuid.uuid4())
        finished_at = datetime.datetime.utcnow().isoformat()
        
        c.execute('''
            INSERT INTO crawl_runs (id, connector, started_at, finished_at, pages, companies_found, new_companies, duplicates, failures, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_id, connector_name, started_at, finished_at,
            stats.get("pages_crawled", 0),
            stats.get("total_found", 0),
            stats.get("added", 0),
            stats.get("duplicates", 0),
            stats.get("failures", 0),
            status
        ))
        conn.commit()
        conn.close()

    def run_all(self):
        logger.info(f"[SourceAggregator] Starting run with {len(self.active_connectors)} active connectors.")
        for connector in sorted(self.active_connectors, key=lambda x: x.priority, reverse=True):
            started_at = datetime.datetime.utcnow().isoformat()
            try:
                logger.info(f"[SourceAggregator] Running {connector.source_name} (v{connector.version})...")
                results = connector.discover_companies()
                
                # Aggregate stats
                added = sum(r.get("added", 0) for r in results)
                pages = sum(r.get("pages_crawled", 1) for r in results)
                total_found = added # Simplify for now
                
                stats = {"added": added, "pages_crawled": pages, "total_found": total_found}
                self.log_crawl_run(connector.source_name, started_at, stats, "SUCCESS")
                
            except Exception as e:
                logger.info(f"[SourceAggregator] Connector {connector.source_name} failed: {e}")
                self.log_crawl_run(connector.source_name, started_at, {"failures": 1}, "FAILED")
                # Isolate failure, continue to next connector
                continue
