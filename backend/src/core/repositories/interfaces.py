from enum import Enum
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

class SchedulerState(str, Enum):
    RUNNING = "RUNNING"
    DRAINING = "DRAINING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class WorkerState(str, Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    STOPPING = "STOPPING"
    OFFLINE = "OFFLINE"
    FAILED = "FAILED"

class CompanyState(str, Enum):
    QUEUED = "QUEUED"
    CRAWLING = "CRAWLING"
    SUCCESS = "SUCCESS"
    RETRY = "RETRY"
    FAILED = "FAILED"
    DISABLED = "DISABLED"

class ICompanyRepository(ABC):
    @abstractmethod
    def get_company(self, provider: str, company_id: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        pass

class ICompanyStateRepository(ABC):
    @abstractmethod
    def acquire_lock(self, provider: str, company_id: str, worker_id: str, tx: Optional[Any] = None) -> bool:
        pass
        
    @abstractmethod
    def update_success(self, provider: str, company_id: str, updates: Dict[str, Any], tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def update_failure(self, provider: str, company_id: str, updates: Dict[str, Any], tx: Optional[Any] = None) -> None:
        pass

class ISessionRepository(ABC):
    @abstractmethod
    def create_session(self, session_id: str, provider: str, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def stop_session(self, session_id: str, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def record_metrics(self, session_id: str, provider: str, metrics: Dict[str, Any], tx: Optional[Any] = None) -> None:
        pass

class WorkerType(str, Enum):
    DISCOVERY = "DISCOVERY"
    VERIFICATION = "VERIFICATION"
    CRAWLER = "CRAWLER"
    APPLY = "APPLY"
    LEARNING = "LEARNING"
    SCHEDULER = "SCHEDULER"

class IWorkerRepository(ABC):
    @abstractmethod
    def register_worker(self, worker_id: str, worker_name: str, worker_type: WorkerType, provider: Optional[str] = None, pid: Optional[int] = None, timeout: int = 60, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def heartbeat(self, worker_id: str, state: WorkerState, current_company_id: Optional[str] = None, current_task: Optional[str] = None, cpu_percent: Optional[float] = None, memory_mb: Optional[float] = None, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def record_progress(self, worker_id: str, jobs_processed: int = 0, jobs_found: int = 0, successes: int = 0, failures: int = 0, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def record_error(self, worker_id: str, error_message: str, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def stop_worker(self, worker_id: str, reason_for_exit: str, tx: Optional[Any] = None) -> None:
        pass

class ISchedulerRepository(ABC):
    @abstractmethod
    def update_state(self, state: SchedulerState, version: str, pid: int, host: str, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def heartbeat(self, tx: Optional[Any] = None) -> None:
        pass

class IProviderRepository(ABC):
    @abstractmethod
    def get_active_providers(self, tx: Optional[Any] = None) -> List[Dict[str, Any]]:
        pass

class IConnectorRepository(ABC):
    @abstractmethod
    def get_connector(self, provider: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        pass

class IJobRepository(ABC):
    @abstractmethod
    def upsert_and_diff(self, jobs: List[Any], board_id: str, synced_at: float, tx: Optional[Any] = None) -> tuple:
        pass

class IMigrationRepository(ABC):
    @abstractmethod
    def get_current_version(self, tx: Optional[Any] = None) -> int:
        pass
        
    @abstractmethod
    def record_migration(self, version: int, name: str, success: bool, tx: Optional[Any] = None) -> None:
        pass
        
    @abstractmethod
    def is_compatible(self, required_version: int, tx: Optional[Any] = None) -> bool:
        pass
