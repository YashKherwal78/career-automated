"""RepositoryManager centralizes repository access and transaction handling.
It owns a database connection (SQLite for now, later PostgreSQL) and lazily
instantiates concrete repository classes.
"""

from __future__ import annotations

from typing import Any

from src.core.repositories.base import BaseRepository
from src.core.repositories.company.metadata import CompanyRepository
from src.core.repositories.company.state import CompanyStateRepository
from src.core.repositories.job.repository import JobRepository
from src.core.repositories.scheduler.worker import WorkerRepository
from src.core.repositories.scheduler.session import SessionRepository
from src.core.repositories.provider.repository import ProviderRepository
from src.core.repositories.connector.repository import ConnectorRepository
from src.core.repositories.scheduler.scheduler import SchedulerRepository
from src.core.repositories.migration.repository import MigrationRepository
from src.core.repositories.outbox.repository import OutboxRepository


class RepositoryManager(BaseRepository):
    """Convenient entry‑point for all repository objects.

    Example usage::

        repos = RepositoryManager()
        with repos.transaction():
            repos.company_state.acquire_lock(...)
            repos.worker.update_heartbeat(...)
    """

    def __init__(self, db_path: str = "boards.db") -> None:
        super().__init__(db_path)
        # Lazily instantiated repositories – created on first access.
        self._company: CompanyRepository | None = None
        self._company_state: CompanyStateRepository | None = None
        self._job: JobRepository | None = None
        self._worker: WorkerRepository | None = None
        self._session: SessionRepository | None = None
        self._provider: ProviderRepository | None = None
        self._connector: ConnectorRepository | None = None
        self._scheduler: SchedulerRepository | None = None
        self._migration: MigrationRepository | None = None
        self._outbox: OutboxRepository | None = None
        self._discovery: Any | None = None
        self._metrics: Any | None = None
        self._cleanup: Any | None = None

    # ---------------------------------------------------------------------
    # Repository properties – instantiated on demand with the shared
    # connection from ``self.get_connection()``.
    # ---------------------------------------------------------------------
    @property
    def discovery(self) -> Any:
        if self._discovery is None:
            from src.core.repositories.discovery.repository import DiscoveryRepository
            self._discovery = DiscoveryRepository(self.db_path)
        return self._discovery

    @property
    def metrics(self) -> Any:
        if self._metrics is None:
            from src.core.repositories.metrics.repository import MetricsRepository
            self._metrics = MetricsRepository(self.db_path)
        return self._metrics

    @property
    def cleanup(self) -> Any:
        if self._cleanup is None:
            from src.core.repositories.scheduler.cleanup import CleanupRepository
            self._cleanup = CleanupRepository(self.db_path)
        return self._cleanup

    @property
    def dashboard(self) -> Any:
        from src.core.repositories.dashboard.repository import DashboardRepository
        # Dashboard doesn't need to be cached as heavily but let's keep pattern
        if not hasattr(self, "_dashboard") or self._dashboard is None:
            self._dashboard = DashboardRepository(self.db_path)
        return self._dashboard

    # ---------------------------------------------------------------------
    # Repository properties – instantiated on demand with the shared
    # connection from ``self.get_connection()``.
    # ---------------------------------------------------------------------
    @property
    def company(self) -> CompanyRepository:
        if self._company is None:
            self._company = CompanyRepository(self.db_path)
        return self._company

    @property
    def company_state(self) -> CompanyStateRepository:
        if self._company_state is None:
            self._company_state = CompanyStateRepository(self.db_path)
        return self._company_state

    @property
    def job(self) -> JobRepository:
        if self._job is None:
            self._job = JobRepository(self.db_path)
        return self._job

    @property
    def worker(self) -> WorkerRepository:
        if self._worker is None:
            self._worker = WorkerRepository(self.db_path)
        return self._worker

    @property
    def session(self) -> SessionRepository:
        if self._session is None:
            self._session = SessionRepository(self.db_path)
        return self._session

    @property
    def provider(self) -> ProviderRepository:
        if self._provider is None:
            self._provider = ProviderRepository(self.db_path)
        return self._provider

    @property
    def connector(self) -> ConnectorRepository:
        if self._connector is None:
            self._connector = ConnectorRepository(self.db_path)
        return self._connector

    @property
    def scheduler(self) -> SchedulerRepository:
        if self._scheduler is None:
            self._scheduler = SchedulerRepository(self.db_path)
        return self._scheduler

    @property
    def outbox(self) -> OutboxRepository:
        if self._outbox is None:
            from src.core.repositories.outbox.repository import OutboxRepository
            self._outbox = OutboxRepository(self.db_path)
        return self._outbox

    @property
    def migration(self) -> MigrationRepository:
        if self._migration is None:
            self._migration = MigrationRepository(self.db_path)
        return self._migration

    # ---------------------------------------------------------------------
    # Transactions are managed via the `transaction` context manager 
    # inherited from BaseRepository, which uses a ContextVar to share
    # the connection automatically.
    # ---------------------------------------------------------------------


