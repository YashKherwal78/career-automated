import sqlite3
import time
import json
import uuid
from typing import Dict, Any
from src.config.settings import settings

class MetricsRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path

    def record_event(self, event_type: str, payload: Dict[str, Any]):
        event_id = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('''
                INSERT INTO pipeline_events (event_id, event_type, payload, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (event_id, event_type, json.dumps(payload), now))
            conn.commit()

    def update_operational_metric(self, key: str, value: Any):
        now = time.time()
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('''
                INSERT INTO operational_metrics (metric_key, metric_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(metric_key) DO UPDATE SET
                    metric_value = excluded.metric_value,
                    updated_at = excluded.updated_at
            ''', (key, str(value), now))
            conn.commit()

    def update_business_metric(self, key: str, value: Any):
        now = time.time()
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('''
                INSERT INTO business_metrics (metric_key, metric_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(metric_key) DO UPDATE SET
                    metric_value = excluded.metric_value,
                    updated_at = excluded.updated_at
            ''', (key, str(value), now))
            conn.commit()

    def get_all_metrics(self) -> Dict[str, Any]:
        metrics = {}
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            
            # Read operational metrics
            cursor = conn.execute("SELECT metric_key, metric_value FROM operational_metrics")
            for row in cursor.fetchall():
                metrics[row["metric_key"]] = row["metric_value"]
                
            # Read business metrics
            cursor = conn.execute("SELECT metric_key, metric_value FROM business_metrics")
            for row in cursor.fetchall():
                metrics[row["metric_key"]] = row["metric_value"]
                
        return metrics
