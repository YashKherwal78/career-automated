"""
Human Review Queue Subsystem (Refinement 6).

Manages low-confidence extractions, conflicting source evidence, and items
requiring explicit user confirmation before merging into Canonical Candidate Profile.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ReviewTask(BaseModel):
    task_id: str
    field_name: str
    reason: str  # e.g., 'source_conflict', 'low_confidence', 'unverified_skill'
    source_a: str
    value_a: Any
    confidence_a: float
    source_b: Optional[str] = None
    value_b: Optional[Any] = None
    confidence_b: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "pending"  # 'pending', 'confirmed_a', 'confirmed_b', 'custom_merged'


class ReviewQueue:
    """Human Review Queue manager."""

    def __init__(self):
        self.tasks: Dict[str, ReviewTask] = {}

    def add_task(self, task: ReviewTask):
        self.tasks[task.task_id] = task

    def get_pending_tasks(self) -> List[ReviewTask]:
        return [t for t in self.tasks.values() if t.status == "pending"]

    def resolve_task(self, task_id: str, resolution: str, custom_value: Optional[Any] = None) -> Any:
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found in Review Queue")
        
        task = self.tasks[task_id]
        task.status = resolution
        if resolution == "confirmed_a":
            return task.value_a
        elif resolution == "confirmed_b":
            return task.value_b
        elif resolution == "custom_merged":
            return custom_value
        return task.value_a
