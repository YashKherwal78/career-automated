import aiohttp
import time
import hashlib
from typing import Dict, Any, Optional, List
from src.discovery.models import FetchResult
from src.discovery.pipeline.caches import ReplayCache
from aiohttp import ClientTimeout

class HttpClient:
    def __init__(self, user_agent: str = "CareerAutomated/1.0", timeout_seconds: float = 10.0, replay_cache: Optional[ReplayCache] = None):
        self.user_agent = user_agent
        self.timeout = ClientTimeout(total=timeout_seconds)
        self.session: Optional[aiohttp.ClientSession] = None
        self.replay_cache = replay_cache
        
    async def __aenter__(self):
        # Increase max field and line sizes to support large headers (e.g. Personio CSP/Cookie headers)
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            max_field_size=32768,
            max_line_size=32768
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch(
        self, 
        method: str, 
        url: str, 
        etag: Optional[str] = None, 
        last_modified: Optional[str] = None, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> FetchResult:
        if not self.session:
            raise RuntimeError("HttpClient must be used as an async context manager")
            
        if self.replay_cache:
            cached = self.replay_cache.get(url, method)
            if cached:
                payload_bytes = cached['payload']
                content_hash = hashlib.sha256(payload_bytes).hexdigest() if payload_bytes else ""
                
                # Automatically decode and parse JSON payload if valid to mirror active fetch behavior
                import json
                payload = payload_bytes
                if payload_bytes:
                    try:
                        payload = json.loads(payload_bytes.decode('utf-8'))
                    except Exception:
                        pass

                res = FetchResult(
                    status_code=cached['status_code'],
                    payload=payload,
                    etag=cached['response_headers'].get("ETag"),
                    last_modified=cached['response_headers'].get("Last-Modified"),
                    content_hash=content_hash,
                    bytes_downloaded=len(payload_bytes) if payload_bytes else 0,
                    response_headers=cached['response_headers'],
                    request_duration_ms=0
                )
                res.final_url = cached['final_url']
                res.redirect_chain = cached['redirect_chain']
                return res
            
        req_headers = dict(headers or {})
        if etag:
            req_headers["If-None-Match"] = etag
        if last_modified:
            req_headers["If-Modified-Since"] = last_modified
            
        start_time = time.time()
        
        async with self.session.request(method, url, headers=req_headers, allow_redirects=True, **kwargs) as response:
            status_code = response.status
            resp_headers = dict(response.headers)
            final_url = str(response.url)
            redirect_chain = [str(r.url) for r in response.history] + [final_url]
            
            payload = None
            payload_bytes = b""
            if status_code != 304 and method != 'HEAD':
                try:
                    payload = await response.json()
                    import json
                    payload_bytes = json.dumps(payload).encode('utf-8')
                except Exception:
                    payload_bytes = await response.read()
                    payload = payload_bytes
                    
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)
            
            content_hash = hashlib.sha256(payload_bytes).hexdigest() if payload_bytes else ""
            
            if self.replay_cache:
                self.replay_cache.set(
                    url=url,
                    method=method,
                    final_url=final_url,
                    status_code=status_code,
                    request_headers=req_headers,
                    response_headers=resp_headers,
                    payload=payload_bytes,
                    redirect_chain=redirect_chain
                )
            
            res = FetchResult(
                status_code=status_code,
                payload=payload,
                etag=resp_headers.get("ETag"),
                last_modified=resp_headers.get("Last-Modified"),
                content_hash=content_hash,
                bytes_downloaded=len(payload_bytes),
                response_headers=resp_headers,
                request_duration_ms=duration_ms
            )
            res.final_url = final_url
            res.redirect_chain = redirect_chain
            return res
