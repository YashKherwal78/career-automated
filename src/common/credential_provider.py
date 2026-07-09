import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Type
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass(repr=False)
class Credential:
    id: str
    provider: str
    secret: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        return f"Credential(id={self.id}, provider={self.provider})"

@dataclass
class CredentialTelemetry:
    provider: str
    credential_id: str
    requests: int = 0
    successes: int = 0
    rate_limits: int = 0
    auth_failures: int = 0
    cooldowns: int = 0
    average_latency: float = 0.0
    last_used: Optional[datetime] = None

class CredentialExhaustedException(Exception):
    pass

class RateLimitException(Exception):
    pass

class AuthException(Exception):
    pass

class CredentialProvider:
    """Abstract Base Class for Credential Management"""
    
    async def execute(self, request_function: Callable[[Credential], Any]) -> Any:
        raise NotImplementedError()
        
    def execute_sync(self, request_function: Callable[[Credential], Any]) -> Any:
        raise NotImplementedError()
        
    def _get_credential(self) -> Credential:
        raise NotImplementedError()
        
    def _report_success(self, credential: Credential, latency_ms: int):
        raise NotImplementedError()
        
    def _report_rate_limit(self, credential: Credential):
        raise NotImplementedError()
        
    def _report_auth_failure(self, credential: Credential):
        raise NotImplementedError()
        
    def get_telemetry(self) -> List[CredentialTelemetry]:
        raise NotImplementedError()


class InMemoryCredentialProvider(CredentialProvider):
    def __init__(self, credentials: List[Credential]):
        self.credentials = credentials
        if not self.credentials:
            raise ValueError("InMemoryCredentialProvider requires at least one credential.")
            
        self.telemetry = {c.id: CredentialTelemetry(provider=c.provider, credential_id=c.id) for c in credentials}
        
        # Internal state tracking
        self._disabled = {c.id: False for c in credentials}
        self._cooldown_until = {c.id: None for c in credentials}
        self.current_index = 0
        
    def _get_credential(self) -> Credential:
        start_idx = self.current_index
        now = datetime.now()
        
        while True:
            c = self.credentials[self.current_index]
            
            # Check if disabled
            if not self._disabled[c.id]:
                # Check if in cooldown
                cooldown_time = self._cooldown_until[c.id]
                if not cooldown_time or cooldown_time <= now:
                    return c
                    
            # Move to next
            self.current_index = (self.current_index + 1) % len(self.credentials)
            
            # If we looped all the way around, no credentials are available
            if self.current_index == start_idx:
                raise CredentialExhaustedException("All credentials are exhausted, on cooldown, or disabled.")
                
    def _report_success(self, credential: Credential, latency_ms: int):
        t = self.telemetry[credential.id]
        t.requests += 1
        t.successes += 1
        t.last_used = datetime.now()
        # Moving average
        if t.successes == 1:
            t.average_latency = latency_ms
        else:
            t.average_latency = (t.average_latency * (t.successes - 1) + latency_ms) / t.successes
            
        # Reset cooldown in case it was incorrectly set
        self._cooldown_until[credential.id] = None

    def _report_rate_limit(self, credential: Credential):
        t = self.telemetry[credential.id]
        t.requests += 1
        t.rate_limits += 1
        t.cooldowns += 1
        t.last_used = datetime.now()
        
        # Place on a 5-minute cooldown
        self._cooldown_until[credential.id] = datetime.now() + timedelta(minutes=5)
        logger.warning(f"Credential {credential.id} hit rate limit. On cooldown for 5 minutes.")
        self.current_index = (self.current_index + 1) % len(self.credentials)

    def _report_auth_failure(self, credential: Credential):
        t = self.telemetry[credential.id]
        t.requests += 1
        t.auth_failures += 1
        t.last_used = datetime.now()
        
        # Permanently disable
        self._disabled[credential.id] = True
        logger.error(f"Credential {credential.id} hit Auth Failure. Permanently disabled.")
        self.current_index = (self.current_index + 1) % len(self.credentials)

    def execute_sync(self, request_function: Callable[[Credential], Any]) -> Any:
        attempts = 0
        max_attempts = len(self.credentials)
        
        while attempts < max_attempts:
            c = self._get_credential()
            start_time = time.time()
            
            try:
                # Call the provider's logic synchronously
                result = request_function(c)
                latency_ms = int((time.time() - start_time) * 1000)
                self._report_success(c, latency_ms)
                return result
                
            except RateLimitException:
                self._report_rate_limit(c)
                attempts += 1
                continue
                
            except AuthException:
                self._report_auth_failure(c)
                attempts += 1
                continue
                
            except Exception as e:
                # Other generic failures, log and raise
                logger.error(f"Credential {c.id} hit unhandled exception: {e}")
                t = self.telemetry[c.id]
                t.requests += 1
                t.last_used = datetime.now()
                raise
                
        raise CredentialExhaustedException("All attempts exhausted.")
        
    async def execute(self, request_function: Callable[[Credential], Any]) -> Any:
        attempts = 0
        max_attempts = len(self.credentials)
        
        while attempts < max_attempts:
            c = self._get_credential()
            start_time = time.time()
            
            try:
                # Call the provider's logic
                result = await request_function(c)
                latency_ms = int((time.time() - start_time) * 1000)
                self._report_success(c, latency_ms)
                return result
                
            except RateLimitException:
                self._report_rate_limit(c)
                attempts += 1
                continue
                
            except AuthException:
                self._report_auth_failure(c)
                attempts += 1
                continue
                
            except Exception as e:
                # Other generic failures, log and raise
                logger.error(f"Credential {c.id} hit unhandled exception: {e}")
                t = self.telemetry[c.id]
                t.requests += 1
                t.last_used = datetime.now()
                raise
                
        raise CredentialExhaustedException("All attempts exhausted.")
        
    def get_telemetry(self) -> List[CredentialTelemetry]:
        return list(self.telemetry.values())


class SQLiteCredentialProvider(CredentialProvider):
    """
    Wraps the existing ApifyManager logic for persistent tracking.
    Never stores the actual secret in SQLite, only the credential ID.
    """
    def __init__(self, credentials: List[Credential]):
        self.credentials = {c.id: c for c in credentials}
        
        # We lazily import ApifyManager to avoid circular dependencies
        from src.integrations.apify_manager import ApifyManager
        self.manager = ApifyManager()
        
        # Register keys in DB
        self.manager.register_credential_ids(list(self.credentials.keys()))
        
    def _get_credential(self) -> Credential:
        key_id_db, credential_id = self.manager.get_active_credential_id()
        if not credential_id or credential_id not in self.credentials:
            raise CredentialExhaustedException("No active Apify credentials available in SQLite.")
        c = self.credentials[credential_id]
        c.config["db_id"] = key_id_db
        return c

    def _report_success(self, credential: Credential, latency_ms: int):
        db_id = credential.config.get("db_id")
        if db_id:
            # We assume a fixed cost for now, ApifyManager handles advanced tracking
            self.manager.record_usage(db_id, category="CredentialProvider", credits=0.01, useful_results=1, success=True)

    def _report_rate_limit(self, credential: Credential):
        db_id = credential.config.get("db_id")
        if db_id:
            self.manager.record_usage(db_id, category="CredentialProvider", credits=0.0, useful_results=0, success=False)

    def _report_auth_failure(self, credential: Credential):
        db_id = credential.config.get("db_id")
        if db_id:
            self.manager.disable_credential(db_id)

    def execute_sync(self, request_function: Callable[[Credential], Any]) -> Any:
        attempts = 0
        max_attempts = len(self.credentials)
        
        while attempts < max_attempts:
            c = self._get_credential()
            start_time = time.time()
            
            try:
                result = request_function(c)
                latency_ms = int((time.time() - start_time) * 1000)
                self._report_success(c, latency_ms)
                return result
            except RateLimitException:
                self._report_rate_limit(c)
                attempts += 1
                continue
            except AuthException:
                self._report_auth_failure(c)
                attempts += 1
                continue
            except Exception as e:
                logger.error(f"Credential {c.id} hit unhandled exception: {e}")
                raise
                
        raise CredentialExhaustedException("All attempts exhausted.")
        
    async def execute(self, request_function: Callable[[Credential], Any]) -> Any:
        attempts = 0
        max_attempts = len(self.credentials)
        
        while attempts < max_attempts:
            c = self._get_credential()
            start_time = time.time()
            
            try:
                result = await request_function(c)
                latency_ms = int((time.time() - start_time) * 1000)
                self._report_success(c, latency_ms)
                return result
            except RateLimitException:
                self._report_rate_limit(c)
                attempts += 1
                continue
            except AuthException:
                self._report_auth_failure(c)
                attempts += 1
                continue
            except Exception as e:
                logger.error(f"Credential {c.id} hit unhandled exception: {e}")
                raise
                
        raise CredentialExhaustedException("All attempts exhausted.")

    def get_telemetry(self) -> List[CredentialTelemetry]:
        return []


@dataclass
class ProviderDefinition:
    name: str
    backend: Type[CredentialProvider]
    credential_loader: Callable[[], List[Credential]]


# --- Loaders ---

def load_google_credentials() -> List[Credential]:
    """
    Pairs GOOGLE_SEARCH_API_KEY_N with GOOGLE_CX_N
    """
    credentials = []
    
    # Check default (no index)
    api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    cx = os.environ.get("GOOGLE_CX")
    if api_key or cx:
        if not api_key or not cx:
            raise ValueError("GOOGLE_SEARCH_API_KEY and GOOGLE_CX must both be provided.")
        credentials.append(Credential(
            id="GOOGLE",
            provider="GOOGLE",
            secret=api_key,
            config={"cx": cx}
        ))
        
    # Check indexed (_1, _2, etc)
    for i in range(1, 10):
        key_name = f"GOOGLE_SEARCH_API_KEY_{i}"
        cx_name = f"GOOGLE_CX_{i}"
        
        api_key_i = os.environ.get(key_name)
        cx_i = os.environ.get(cx_name)
        
        if api_key_i or cx_i:
            if not api_key_i or not cx_i:
                raise ValueError(f"{key_name} and {cx_name} must both be provided.")
            credentials.append(Credential(
                id=f"GOOGLE_{i}",
                provider="GOOGLE",
                secret=api_key_i,
                config={"cx": cx_i}
            ))
            
    if not credentials:
        logger.warning("No Google credentials found in environment.")
        
    return credentials

def load_generic_credentials(provider_name: str, prefix: str) -> List[Credential]:
    """
    Loads keys like PREFIX, PREFIX_1, PREFIX_2, etc.
    """
    credentials = []
    
    default_key = os.environ.get(prefix)
    if default_key:
        credentials.append(Credential(id=provider_name, provider=provider_name, secret=default_key))
        
    # Also support EXA_API_KEY_FALLBACK
    if prefix == "EXA_API_KEY":
        fb = os.environ.get("EXA_API_KEY_FALLBACK")
        if fb and fb not in [c.secret for c in credentials]:
            credentials.append(Credential(id=f"{provider_name}_FALLBACK", provider=provider_name, secret=fb))
            
    for i in range(1, 20):
        key = os.environ.get(f"{prefix}_{i}")
        if key and key not in [c.secret for c in credentials]:
            credentials.append(Credential(id=f"{provider_name}_{i}", provider=provider_name, secret=key))
            
    if not credentials:
        logger.warning(f"No credentials found for {provider_name} (prefix: {prefix}).")
        
    return credentials


# --- Registry ---

PROVIDERS = {
    "EXA": ProviderDefinition(
        name="EXA", 
        backend=InMemoryCredentialProvider, 
        credential_loader=lambda: load_generic_credentials("EXA", "EXA_API_KEY")
    ),
    "GOOGLE": ProviderDefinition(
        name="GOOGLE", 
        backend=InMemoryCredentialProvider, 
        credential_loader=load_google_credentials
    ),
    "GROQ": ProviderDefinition(
        name="GROQ", 
        backend=InMemoryCredentialProvider, 
        credential_loader=lambda: load_generic_credentials("GROQ", "GROQ_API_KEY")
    ),
    "FIRECRAWL": ProviderDefinition(
        name="FIRECRAWL", 
        backend=InMemoryCredentialProvider, 
        credential_loader=lambda: load_generic_credentials("FIRECRAWL", "FIRECRAWL_API_KEY")
    ),
    "JINA": ProviderDefinition(
        name="JINA", 
        backend=InMemoryCredentialProvider, 
        credential_loader=lambda: load_generic_credentials("JINA", "JINA_API_KEY")
    ),
    "APIFY": ProviderDefinition(
        name="APIFY", 
        backend=SQLiteCredentialProvider, 
        credential_loader=lambda: load_generic_credentials("APIFY", "APIFY_KEY") # APIFY_KEY_1... Note: APIFY_API_KEY exists too
    ),
}

class CredentialFactory:
    _instances: Dict[str, CredentialProvider] = {}
    
    @classmethod
    def get(cls, provider: str) -> CredentialProvider:
        if provider in cls._instances:
            return cls._instances[provider]
            
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider requested from CredentialFactory: {provider}")
            
        definition = PROVIDERS[provider]
        
        # Validate startup
        credentials = definition.credential_loader()
        if not credentials:
            # We don't hard crash if 0 credentials (some providers might be disabled),
            # but maybe we should for critical ones. 
            pass
            
        # Ensure no duplicates in IDs
        ids = [c.id for c in credentials]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate credential IDs detected for provider {provider}")
            
        for c in credentials:
            if not c.secret:
                raise ValueError(f"Credential {c.id} loaded with empty secret.")
                
        # Instantiate backend
        backend_instance = definition.backend(credentials)
        cls._instances[provider] = backend_instance
        
        return backend_instance
