import sqlite3
import time
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from src.config.settings import settings

logger = logging.getLogger("ReservationRepository")

class WorkReservationRepository(ABC):
    @abstractmethod
    def reserve_due_board(self, worker_id: str, lock_duration: int = 300) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def mark_completed(self, company_id: str, token: str, interval: int):
        pass

    @abstractmethod
    def mark_failed(self, company_id: str, token: str, backoff_schedule: List[int]):
        pass

class SQLiteReservationRepository(WorkReservationRepository):
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path

    def reserve_due_board(self, worker_id: str, lock_duration: int = 300) -> Optional[Dict[str, Any]]:
        from src.api.db import get_connection, is_postgres
        now = time.time()
        # Single atomic check-and-lock
        conn = get_connection()
        try:
            # PostgreSQL locks rows with SELECT FOR UPDATE, SQLite locks the entire database with BEGIN IMMEDIATE
            if is_postgres():
                # Locate due board and lock it
                cursor = conn.execute('''
                    SELECT id, company_id, priority, last_job_sync FROM ats_registry
                    WHERE status = 'ACTIVE'
                      AND (reservation_token IS NULL OR reserved_until <= %s)
                      AND (next_check_at IS NULL OR next_check_at <= %s)
                    ORDER BY priority DESC, last_job_sync ASC
                    LIMIT 1
                    FOR UPDATE
                ''', (now, now))
            else:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.execute('''
                    SELECT * FROM ats_registry
                    WHERE status = 'ACTIVE'
                      AND (reservation_token IS NULL OR reserved_until <= ?)
                      AND (next_check_at IS NULL OR next_check_at <= ?)
                    ORDER BY priority DESC, last_job_sync ASC
                    LIMIT 1
                ''', (now, now))
                
            row = cursor.fetchone()
            if not row:
                if not is_postgres():
                    conn.rollback()
                return None

            board_data = dict(row)
            company_id = board_data["company_id"]
            token = f"{worker_id}-{uuid.uuid4().hex[:8]}"

            # Lock the board
            if is_postgres():
                cursor_update = conn.execute('''
                    UPDATE ats_registry
                    SET reservation_token = %s,
                        reserved_by = %s,
                        reserved_until = %s
                    WHERE company_id = %s
                      AND status = 'ACTIVE'
                      AND (reservation_token IS NULL OR reserved_until <= %s)
                ''', (token, worker_id, now + lock_duration, company_id, now))
            else:
                cursor_update = conn.execute('''
                    UPDATE ats_registry
                    SET reservation_token = ?,
                        reserved_by = ?,
                        reserved_until = ?
                    WHERE company_id = ?
                      AND status = 'ACTIVE'
                      AND (reservation_token IS NULL OR reserved_until <= ?)
                ''', (token, worker_id, now + lock_duration, company_id, now))

            if cursor_update.rowcount > 0:
                board_data["reservation_token"] = token
                board_data["reserved_by"] = worker_id
                board_data["reserved_until"] = now + lock_duration
                conn.commit()
                return board_data
            else:
                # Race condition lost
                if not is_postgres():
                    conn.rollback()
                return None
        except Exception as e:
            if not is_postgres():
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"Error in reserve_due_board: {e}")
            return None
        finally:
            conn.close()

    def mark_completed(self, company_id: str, token: str, interval: int):
        from src.api.db import get_connection, is_postgres
        now = time.time()
        next_check = now + interval
        conn = get_connection()
        try:
            if is_postgres():
                conn.execute('''
                    UPDATE ats_registry
                    SET last_job_sync = %s,
                        last_successful_crawl = %s,
                        failure_count = 0,
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until = 0.0,
                        next_check_at = %s
                    WHERE company_id = %s AND reservation_token = %s
                ''', (now, now, next_check, company_id, token))
            else:
                conn.execute('''
                    UPDATE ats_registry
                    SET last_job_sync = ?,
                        last_successful_crawl = ?,
                        failure_count = 0,
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until = 0.0,
                        next_check_at = ?
                    WHERE company_id = ? AND reservation_token = ?
                ''', (now, now, next_check, company_id, token))
            conn.commit()
            logger.info(f"Board {company_id} sync completed. Next check at {next_check}")
        finally:
            conn.close()

    def mark_failed(self, company_id: str, token: str, backoff_schedule: List[int]):
        from src.api.db import get_connection, is_postgres
        now = time.time()
        conn = get_connection()
        try:
            # 1. Fetch current failure count
            if is_postgres():
                cursor = conn.execute("SELECT failure_count FROM ats_registry WHERE company_id = %s", (company_id,))
            else:
                cursor = conn.execute("SELECT failure_count FROM ats_registry WHERE company_id = ?", (company_id,))
            row = cursor.fetchone()
            failures = row[0] if row else 0
            failures += 1

            # 2. Compute backoff
            index = min(failures - 1, len(backoff_schedule) - 1)
            backoff = backoff_schedule[index]
            next_check = now + backoff

            # 3. Update fields and release lock
            if is_postgres():
                conn.execute('''
                    UPDATE ats_registry
                    SET failure_count = %s,
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until = 0.0,
                        next_check_at = %s
                    WHERE company_id = %s AND reservation_token = %s
                ''', (failures, next_check, company_id, token))
            else:
                conn.execute('''
                    UPDATE ats_registry
                    SET failure_count = ?,
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until = 0.0,
                        next_check_at = ?
                    WHERE company_id = ? AND reservation_token = ?
                ''', (failures, next_check, company_id, token))
            conn.commit()
            logger.warning(f"Board {company_id} sync failed (Failures: {failures}). Retrying in {backoff}s")
        finally:
            conn.close()
