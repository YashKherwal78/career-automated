import sqlite3
import aiohttp
import asyncio
import logging
from typing import List
from src.discovery.registry.ats_providers import ProviderRegistry, VerificationResult, EndpointIdentity

logger = logging.getLogger("EndpointValidationEngine")

class EndpointValidationEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    async def validate_endpoints(self, target_list: List[tuple] = None) -> List[VerificationResult]:
        if target_list is not None:
            targets = target_list
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Query career_endpoints with company name from identities
            c.execute('''
                SELECT e.endpoint_id, e.company_id, e.career_url, e.ats_provider, c.legal_name
                FROM career_endpoints e
                JOIN company_identities c ON e.company_id = c.company_id
                WHERE e.status = 'DISCOVERED_ENDPOINT' OR e.status = 'VERIFYING'
            ''')
            targets = c.fetchall()
            conn.close()
            
        if not targets:
            return []
            
        results = []
        
        async with aiohttp.ClientSession() as session:
            # We can run checks concurrently using asyncio.gather
            async def validate_single(eid, cid, url, ats, company_name):
                # Try to resolve provider by name or by URL
                provider = ProviderRegistry.get_provider_by_name(ats)
                if not provider:
                    provider = ProviderRegistry.resolve(url)
                    
                if not provider:
                    # Return a failed verification result
                    return VerificationResult(
                        endpoint_id=eid,
                        company_id=cid,
                        company_name=company_name,
                        provider=ats or "Unknown",
                        endpoint=url,
                        canonical_endpoint=url,
                        endpoint_identity=EndpointIdentity(provider=ats or "Unknown", identifiers={}),
                        healthy=False,
                        verified=False,
                        confidence=0.0,
                        inspector_score=0.0,
                        identity_score=0.0,
                        reason=f"Unknown ATS provider: '{ats}'",
                        metadata={},
                        plugin_name="None",
                        plugin_version="1.0",
                        provider_version="None",
                        latency_ms=0
                    )
                
                # Perform verification via base provider logic
                try:
                    return await provider.verify(session, url, company_name, eid, cid)
                except Exception as e:
                    return VerificationResult(
                        endpoint_id=eid,
                        company_id=cid,
                        company_name=company_name,
                        provider=provider.name,
                        endpoint=url,
                        canonical_endpoint=url,
                        endpoint_identity=EndpointIdentity(provider=provider.name, identifiers={}),
                        healthy=False,
                        verified=False,
                        confidence=0.0,
                        inspector_score=0.0,
                        identity_score=0.0,
                        reason=str(e),
                        metadata={},
                        plugin_name=provider.__class__.__name__,
                        plugin_version=provider.plugin_version,
                        provider_version=provider.provider_version,
                        latency_ms=0
                    )

            tasks = [validate_single(eid, cid, url, ats, name) for eid, cid, url, ats, name in targets]
            results = await asyncio.gather(*tasks)
            
        return list(results)
