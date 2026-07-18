import uuid
import json
from typing import Optional, Any, Dict, List
from src.core.repositories.base import BaseRepository

class OutboxRepository(BaseRepository):
    def save_event(self, event_type: str, aggregate_type: str, aggregate_id: str, payload: Dict[str, Any], correlation_id: Optional[str] = None, trace_id: Optional[str] = None, tx: Optional[Any] = None) -> None:
        event_id = uuid.uuid4()
        corr_id = correlation_id or uuid.uuid4()
        tr_id = trace_id or uuid.uuid4()
        payload_str = json.dumps(payload)
        with self.transaction() as conn:
            conn.execute('''
                INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload, correlation_id, trace_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (event_id, event_type, aggregate_type, aggregate_id, payload_str, corr_id, tr_id))

    def claim_pending_events(self, batch_size: int = 50, tx: Optional[Any] = None) -> List[Dict[str, Any]]:
        with self.transaction() as conn:
            cursor = conn.execute('''
                WITH claimed AS (
                    SELECT event_id FROM outbox_events
                    WHERE status = 'PENDING' 
                      AND (next_retry_at IS NULL OR next_retry_at <= NOW())
                    LIMIT %s FOR UPDATE SKIP LOCKED
                )
                UPDATE outbox_events e
                SET status = 'PROCESSING', 
                    last_attempt_at = NOW(),
                    attempt_count = attempt_count + 1
                FROM claimed c
                WHERE e.event_id = c.event_id
                RETURNING e.*;
            ''', (batch_size,))
            return [dict(r) if hasattr(r, 'keys') else dict(zip([col[0] for col in cursor.description], r)) for r in cursor.fetchall()]

    def mark_delivered(self, event_id: str, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            conn.execute('''
                UPDATE outbox_events
                SET status = 'DELIVERED', delivered_at = NOW()
                WHERE event_id = %s
            ''', (event_id,))

    def mark_delivered_batch(self, event_ids: List[str], tx: Optional[Any] = None) -> None:
        if not event_ids:
            return
        with self.transaction() as conn:
            conn.execute('''
                UPDATE outbox_events
                SET status = 'DELIVERED', delivered_at = NOW()
                WHERE event_id = ANY(%s)
            ''', (event_ids,))

    def mark_failed(self, event_id: str, error_message: str, max_retries: int = 10, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            cur = conn.execute("SELECT attempt_count FROM outbox_events WHERE event_id = %s", (event_id,))
            row = cur.fetchone()
            attempts = (row["attempt_count"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) if row else 1
            
            if attempts >= max_retries:
                conn.execute('''
                    UPDATE outbox_events
                    SET status = 'FAILED', last_error = %s
                    WHERE event_id = %s
                ''', (error_message, event_id))
            else:
                import random
                delay_sec = (2 ** attempts) * 10 + random.randint(1, 5)
                import datetime
                next_retry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay_sec)
                conn.execute('''
                    UPDATE outbox_events
                    SET status = 'PENDING', next_retry_at = %s, last_error = %s
                    WHERE event_id = %s
                ''', (next_retry, error_message, event_id))

    def prune_delivered_events(self, days_old: int = 30, tx: Optional[Any] = None) -> int:
        with self.transaction() as conn:
            cur = conn.execute('''
                DELETE FROM outbox_events
                WHERE status = 'DELIVERED' AND delivered_at < NOW() - (CAST(%s AS TEXT) || ' days')::INTERVAL
            ''', (days_old,))
            return cur.rowcount
