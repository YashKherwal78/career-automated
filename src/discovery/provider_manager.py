from typing import List
import importlib
import pkgutil
import src.discovery.providers
from src.discovery.providers.base_provider import BaseProvider

class ProviderManager:
    def __init__(self):
        self.providers = []
        self._load_providers()
        
    def _load_providers(self):
        # Dynamically load all classes in src.discovery.providers that inherit from BaseProvider
        package = src.discovery.providers
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            if module_name == 'base_provider':
                continue
            module = importlib.import_module(f"src.discovery.providers.{module_name}")
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isinstance(attribute, type) and issubclass(attribute, BaseProvider) and attribute is not BaseProvider:
                    try:
                        self.providers.append(attribute())
                    except Exception as e:
                        print(f"Failed to instantiate {attribute_name}: {e}")

    def fetch_opportunities(self, company_name: str) -> List[dict]:
        all_opportunities = []
        
        for provider in self.providers:
            # We don't assume ATS. Every provider gets a chance to fetch jobs for the company.
            try:
                # We need to adapt the provider's API. Most providers have `_discover_jobs_internal(last_sync)`
                # Let's assume for now the provider can be queried for a specific company if we modify them,
                # or we just trigger them. For this Sprint 1.1 abstraction, we will simulate the competition
                # interface that returns opportunities.
                
                # In a real implementation, we would pass `company_name` to the provider.
                pass
            except Exception as e:
                print(f"Provider {provider.__class__.__name__} failed for {company_name}: {e}")
                
        return all_opportunities
