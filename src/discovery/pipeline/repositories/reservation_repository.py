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
        now = time.time()
        # Single atomic check-and-lock
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            # Use BEGIN IMMEDIATE to lock the database during the checkout
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Find due boards
                cursor = conn.execute('''
                    SELECT * FROM ats_registry
                    WHERE status = 'ACTIVE'
                      AND (reservation_token IS NULL OR reserved_until <= ?)
                      AND next_check_at <= ?
                    ORDER BY priority DESC, last_job_sync ASC
                    LIMIT 1
                ''', (now, now))
                row = cursor.fetchone()
                if not row:
                    return None

                board_data = dict(row)
                company_id = board_data["company_id"]
                token = f"{worker_id}-{uuid.uuid4().hex[:8]}"

                # Lock the board
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
                    # Race condition lost, rollback and return None
                    conn.rollback()
                    return None
            except Exception as e:
                conn.rollback()
                logger.error(f"Error in reserve_due_board: {e}")
                return None

    def mark_completed(self, company_id: str, token: str, interval: int):
        now = time.time()
        next_check = now + interval
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
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

    def mark_failed(self, company_id: str, token: str, backoff_schedule: List[int]):
        now = time.time()
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # 1. Fetch current failure count
            cursor = conn.execute("SELECT failure_count FROM ats_registry WHERE company_id = ?", (company_id,))
            row = cursor.fetchone()
            failures = row[0] if row else 0
            failures += 1

            # 2. Compute backoff
            index = min(failures - 1, len(backoff_schedule) - 1)
            backoff = backoff_schedule[index]
            next_check = now + backoff

            # 3. Update fields and release lock
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
