# src/discovery/state_machine.py
"""Crawl state machine and structured event emission.
Defines the allowed transitions for a board's lifecycle and provides a thin
wrapper around the reservation repository to persist state changes.
"""
import enum
from typing import Any, Dict

class CrawlState(enum.Enum):
    DISCOVERED = "DISCOVERED"
    RESERVED = "RESERVED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"
    DISABLED = "DISABLED"

class CrawlStateMachine:
    def __init__(self, repo, event_bus):
        self.repo = repo
        self.bus = event_bus

    def _emit(self, event_name: str, payload: Dict[str, Any]):
        if self.bus:
            self.bus.emit(event_name, payload)

    def reserve(self, board_id: int, lease_id: str, lease_version: int, lease_until: float):
        self.repo.update_state(board_id, CrawlState.RESERVED, lease_id, lease_version, lease_until)
        self._emit("BOARD_RESERVED", {"board_id": board_id, "lease_id": lease_id, "lease_version": lease_version})

    def enqueue(self, board_id: int):
        self.repo.update_state(board_id, CrawlState.QUEUED)
        self._emit("BOARD_QUEUED", {"board_id": board_id})

    def start(self, board_id: int, job_version: int):
        self.repo.update_state(board_id, CrawlState.RUNNING, job_version=job_version)
        self._emit("BOARD_STARTED", {"board_id": board_id, "job_version": job_version})

    def succeed(self, board_id: int):
        self.repo.update_state(board_id, CrawlState.ACTIVE)
        self._emit("BOARD_SUCCEEDED", {"board_id": board_id})

    def fail(self, board_id: int, reason: str):
        self.repo.update_state(board_id, CrawlState.FAILED)
        self._emit("BOARD_FAILED", {"board_id": board_id, "reason": reason})

    def dead_letter(self, board_id: int, reason: str):
        self.repo.update_state(board_id, CrawlState.DEAD_LETTER)
        self._emit("BOARD_DEAD_LETTER", {"board_id": board_id, "reason": reason})

    def disable(self, board_id: int):
        self.repo.update_state(board_id, CrawlState.DISABLED)
        self._emit("BOARD_DISABLED", {"board_id": board_id})
