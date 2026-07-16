from src.api.db import get_connection
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Callable, List
from src.config.config import Config

DB_PATH = Config.DATABASE_PATH

class EventBus:
    """
    A lightweight, SQLite-backed event bus for decoupling the Discovery pipeline.
    Ensures idempotency, retryability, and resumability.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def publish(self, event_type: str, payload: Dict[str, Any]):
        """Publishes an event to the system_events table."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_events (event_type, payload, status)
            VALUES (?, ?, 'PENDING')
        ''', (event_type, json.dumps(payload)))
        conn.commit()
        conn.close()

    def subscribe(self, event_type: str, handler: Callable):
        """Registers an in-process handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def process_pending_events(self, limit: int = 100):
        """
        Polls the system_events table for PENDING events and executes their registered handlers.
        Marks events as COMPLETED or FAILED.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM system_events 
            WHERE status = 'PENDING' OR (status = 'FAILED' AND retry_count < 3)
            ORDER BY created_at ASC LIMIT ?
        ''', (limit,))
        events = cursor.fetchall()
        
        for event in events:
            event_id = event['id']
            event_type = event['event_type']
            payload = json.loads(event['payload'])
            retry_count = event['retry_count']
            
            handlers = self._handlers.get(event_type, [])
            if not handlers:
                # No handlers registered for this event type yet
                continue
                
            success = True
            error_message = None
            
            for handler in handlers:
                try:
                    handler(payload)
                except Exception as e:
                    success = False
                    error_message = str(e)
                    break # Stop on first handler failure to allow retry of the whole event
                    
            if success:
                cursor.execute('''
                    UPDATE system_events 
                    SET status = 'COMPLETED', processed_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (event_id,))
            else:
                new_status = 'FAILED' if retry_count < 2 else 'DEAD_LETTER'
                cursor.execute('''
                    UPDATE system_events 
                    SET status = ?, error_message = ?, retry_count = retry_count + 1, processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_status, error_message, event_id))
                
            conn.commit()
            
        conn.close()

# Global singleton
event_bus = EventBus()
