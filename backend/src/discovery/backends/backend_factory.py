import os
from src.discovery.backends.base_backend import BaseBackend
from src.discovery.backends.native_http_backend import NativeHTTPBackend

class BackendFactory:
    """
    Globally instantiates the active backend based on configuration/environment variables.
    """
    @staticmethod
    def get_backend() -> BaseBackend:
        backend_type = os.environ.get("DISCOVERY_BACKEND", "http").lower()
        
        if backend_type == "http":
            return NativeHTTPBackend()
        elif backend_type == "apify":
            # return ApifyBackend() # Placeholder for future implementation
            raise NotImplementedError("Apify backend not yet implemented.")
        elif backend_type == "serp":
            # return SerpBackend()
            raise NotImplementedError("SERP backend not yet implemented.")
        else:
            return NativeHTTPBackend()
