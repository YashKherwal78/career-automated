import os
import importlib
import inspect
import concurrent.futures
from typing import List, Dict, Type
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderStatus

class ProviderManager:
    """
    Dynamically loads all providers from the providers directory that inherit from BaseProvider.
    Checks configuration validation before running them.
    Executes in parallel.
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
                        if issubclass(obj, BaseProvider) and obj is not BaseProvider:
                            if obj.__module__ == module_name:
                                provider_instance = obj()
                                self.providers.append(provider_instance)
                except Exception as e:
                    print(f"Failed to load provider {filename}: {e}")

    def run_all_providers(self, last_sync_timestamps: Dict[str, str] = None, target_companies: List[Dict] = None) -> List[StandardJob]:
        """
        Runs all registered providers in parallel, respecting their validation status and incremental sync timestamp.
        """
        all_jobs = []
        if last_sync_timestamps is None:
            last_sync_timestamps = {}
            
        def run_provider(provider):
            if not provider.validate_configuration():
                provider.status.record_failure("Missing API Configuration or Failed Health Check")
                print(f"Skipping {provider.name}: Missing Configuration")
                return []
                
            last_sync = last_sync_timestamps.get(provider.name)
            if not provider.capabilities.supports_incremental_sync:
                last_sync = None
                
            try:
                # Assuming provider.discover_jobs takes last_sync_timestamp
                jobs = provider.discover_jobs(last_sync)
                return jobs
            except Exception as e:
                provider.status.record_failure(str(e))
                return []

        print(f"ProviderManager: Launching {len(self.providers)} providers in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_provider = {executor.submit(run_provider, p): p for p in self.providers}
            for future in concurrent.futures.as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    jobs = future.result()
                    if jobs:
                        all_jobs.extend(jobs)
                except Exception as exc:
                    print(f'{provider.name} generated an exception: {exc}')
                    
        # Normalization and Deduplication
        return self._normalize_and_deduplicate(all_jobs)
        
    def _normalize_and_deduplicate(self, jobs: List[StandardJob]) -> List[StandardJob]:
        seen_urls = set()
        deduped = []
        for job in jobs:
            # Normalize
            job.company = job.company.strip().title() if job.company else "Unknown Company"
            job.role = job.role.strip() if job.role else "Unknown Role"
            
            # Deduplicate by absolute application URL
            if job.application_url:
                url = job.application_url.strip().lower()
                if url not in seen_urls:
                    seen_urls.add(url)
                    deduped.append(job)
            else:
                deduped.append(job)
                
        return deduped
        
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
