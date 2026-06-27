import os
import importlib
import inspect
from typing import List, Dict, Type
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderStatus

class ProviderManager:
    """
    Dynamically loads all providers from the providers directory that inherit from BaseProvider.
    Checks configuration validation before running them.
    """
    def __init__(self):
        self.providers: List[BaseProvider] = []
        self._load_providers()
        
    def _load_providers(self):
        providers_dir = os.path.dirname(__file__)
        for filename in os.listdir(providers_dir):
            if filename.endswith("_provider.py") and filename != "base_provider.py":
                module_name = f"src.discovery.providers.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # Ensure it's a subclass of BaseProvider and not BaseProvider itself
                        if issubclass(obj, BaseProvider) and obj is not BaseProvider:
                            # Also check if it's actually defined in this module
                            if obj.__module__ == module_name:
                                provider_instance = obj()
                                self.providers.append(provider_instance)
                except Exception as e:
                    print(f"Failed to load provider {filename}: {e}")

    def run_all_providers(self, last_sync_timestamps: Dict[str, str] = None, target_companies: List[Dict] = None) -> List[StandardJob]:
        """
        Runs all registered providers, respecting their validation status and incremental sync timestamp.
        """
        all_jobs = []
        if last_sync_timestamps is None:
            last_sync_timestamps = {}
            
        for provider in self.providers:
            # Priority 0: Configuration Validation
            if not provider.validate_configuration():
                provider.status.record_failure("Missing API Configuration or Failed Health Check")
                print(f"Skipping {provider.name}: Missing Configuration")
                continue
                
            last_sync = last_sync_timestamps.get(provider.name)
            if not provider.capabilities.supports_incremental_sync:
                last_sync = None
                
            jobs = provider.discover_jobs(last_sync, target_companies)
            all_jobs.extend(jobs)
            
        return all_jobs
        
    def get_health_report(self) -> str:
        lines = [
            "# Provider Health Report",
            "",
            "| Provider | Status | Jobs Found | Average Latency | Last Sync | Failures |",
            "|----------|--------|------------|-----------------|-----------|----------|"
        ]
        
        for p in self.providers:
            status_text = "Healthy" if p.status.healthy else "Failed"
            jobs = p.status.jobs_found
            latency = f"{p.status.average_response_time:.2f}s"
            last_sync = p.status.last_success or "Never"
            failure = p.status.failure_reason or ""
            
            lines.append(f"| {p.name} | {status_text} | {jobs} | {latency} | {last_sync} | {failure} |")
            
        return "\n".join(lines)
