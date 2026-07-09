import asyncio
import time
import logging
from typing import List, Dict, Any, Optional

from src.discovery.pipeline.fallback_models import (
    DiscoveryBudget, Evidence, Candidate, DiscoverySource, DiscoveryPlugin, VerificationPolicy, VerificationResult
)
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.pipeline.caches import ReplayCache
from src.discovery.pipeline.url_canonicalizer import URLCanonicalizer
from src.discovery.pipeline.ats_registry import ATSRegistry
import hashlib

logger = logging.getLogger("DiscoveryOrchestrator")

class DiscoveryContext:
    def __init__(self, company: str, website: str, budget: DiscoveryBudget, http: HttpClient, replay_cache: Optional[ReplayCache], logger: logging.Logger, ats_domains: List[str]):
        self.company = company
        self.website = website
        self.budget = budget
        self.http = http
        self.replay_cache = replay_cache
        self.logger = logger
        self.ats_domains = ats_domains
        self.candidate_pool = []
        
        self.requests_used = 0
        self.bytes_downloaded = 0
        self.search_queries_used = 0
        
    async def fetch(self, method: str, url: str, **kwargs):
        if self.requests_used >= self.budget.max_http_requests:
            raise RuntimeError("HTTP request budget exceeded")
        self.requests_used += 1
        res = await self.http.fetch(method, url, **kwargs)
        if res:
            self.bytes_downloaded += res.bytes_downloaded
        return res
        
    async def head(self, url: str, **kwargs):
        return await self.fetch('HEAD', url, **kwargs)

class DiscoveryOrchestrator:
    def __init__(self, sources: List[DiscoverySource], plugins: List[DiscoveryPlugin], replay_cache: Optional[ReplayCache] = None):
        self.sources = sources
        self.plugins = plugins
        self.replay_cache = replay_cache
        self.registry = ATSRegistry()
        self.ats_domains = []
        for p in self.plugins:
            self.ats_domains.extend(p.candidate_domains())
        
    def _apply_known_ats_penalties(self, candidates: List[Candidate], html_content: str):
        penalty = 0
        if "greenhouse.io" in html_content:
            penalty -= 30
        if "jobs.lever.co" in html_content:
            penalty -= 30
        if "eightfold.ai" in html_content:
            penalty -= 40
        if "icims.com" in html_content:
            penalty -= 30
            
        if penalty < 0:
            for c in candidates:
                c.evidence.append(Evidence(source="Known ATS Penalty", weight=penalty, description="Found competing ATS signature in HTML"))

    async def execute(self, company: str, website: str, budget: DiscoveryBudget) -> Dict[str, Any]:
        start_time = time.time()
        
        # Determine company_id (we'll use website domain as canonical ID if not passed differently)
        # Ideally, `company` argument is the company_id, but here we canonicalize it.
        from urllib.parse import urlparse
        parsed = urlparse(website if website.startswith('http') else f"https://{website}")
        company_domain = parsed.netloc.replace('www.', '')
        company_id = company_domain  # Treat domain as company_id for now
        
        active_endpoint = self.registry.get_active_endpoint(company_id)
        if active_endpoint:
            now = time.time()
            if active_endpoint['recheck_after'] and now < active_endpoint['recheck_after']:
                # Bypass completely
                logger.info(f"Registry-First: {company} reusing active endpoint {active_endpoint['endpoint']} without network call.")
                return {
                    "verified": [active_endpoint],
                    "all_candidates": [],
                    "funnel": {"registry_bypassed": True},
                    "duration": time.time() - start_time
                }
            
            # Lightweight check needed
            for plugin in self.plugins:
                if plugin.provider_name == active_endpoint['ats_type']:
                    is_healthy = await plugin.health_check(active_endpoint['endpoint'])
                    if is_healthy:
                        new_recheck = now + plugin.recheck_policy('ACTIVE')
                        self.registry.record_health_check(active_endpoint['id'], 'ACTIVE', new_recheck)
                        active_endpoint['last_checked'] = now
                        active_endpoint['recheck_after'] = new_recheck
                        logger.info(f"Registry-First: {company} health check passed for {active_endpoint['endpoint']}.")
                        return {
                            "verified": [active_endpoint],
                            "all_candidates": [],
                            "funnel": {"health_check_passed": True},
                            "duration": time.time() - start_time
                        }
                    else:
                        new_recheck = now + plugin.recheck_policy('FAILED')
                        self.registry.record_health_check(active_endpoint['id'], 'FAILED', new_recheck)
                        logger.info(f"Registry-First: {company} health check failed. Proceeding to rediscovery.")
                        break
        
        candidate_pool: Dict[str, Candidate] = {}
        
        async with HttpClient(replay_cache=self.replay_cache) as http:
            context = DiscoveryContext(
                company=company,
                website=website,
                budget=budget,
                http=http,
                replay_cache=self.replay_cache,
                logger=logger,
                ats_domains=self.ats_domains
            )
            
            # 1. Candidate Generation
            for source in self.sources:
                context.candidate_pool = list(candidate_pool.values())

                try:
                    result = await source.discover(context)
                    # Deduplicate and accumulate
                    for c in result.candidates:
                        canonical_url = URLCanonicalizer.canonicalize(c.url)
                        if canonical_url not in candidate_pool:
                            c.url = canonical_url
                            candidate_pool[canonical_url] = c
                        else:
                            candidate_pool[canonical_url].evidence.extend(c.evidence)
                            # Preserve telemetry if missing
                            for field in ['search_provider', 'search_query', 'search_rank', 'search_title']:
                                if not getattr(candidate_pool[canonical_url], field, None) and getattr(c, field, None):
                                    setattr(candidate_pool[canonical_url], field, getattr(c, field))
                except Exception as e:
                    logger.error(f"Source {source.__class__.__name__} failed for {company}: {e}")

            # 2. Additive Scoring & Parser Confidence
            scored_candidates = list(candidate_pool.values())
            
            try:
                # We do a direct fetch since this is orchestrator level
                res = await http.fetch('GET', website)
                if res and res.payload:
                    self._apply_known_ats_penalties(scored_candidates, res.payload.decode('utf-8', errors='ignore'))
            except Exception:
                pass

            # 3. Apply Parser and Funnel Telemetry
            valid_candidates = []
            funnel = {
                "generated": len(scored_candidates),
                "parsed": 0,
                "score_passed": 0,
                "validation_passed": 0,
                "inspected": 0,
                "skipped_score": 0,
                "skipped_validation": 0,
                "skipped_budget": 0
            }
            
            for plugin in self.plugins:
                for c in scored_candidates:
                    identity, conf, reason = plugin.parse_candidate(c.url)
                    if identity:
                        c.parsed_identity = identity
                        c.parser_success = True
                        c.parser_confidence = conf
                        c.parser_reason = reason
                        valid_candidates.append(c)
                    else:
                        c.parser_success = False
                        c.parser_reason = reason
                        
            funnel["parsed"] = len(valid_candidates)
                        
            # Sort by candidate_score * parser_confidence
            valid_candidates.sort(key=lambda c: c.score * c.parser_confidence, reverse=True)
            
            # 4. Identity Pre-filter and Score Filter
            policy = self.verification_policy if hasattr(self, 'verification_policy') else VerificationPolicy()
            scored_valid = []
            from src.discovery.pipeline.identity_validator import CompanyIdentityValidator
            
            for c in valid_candidates:
                # Run Pre-filter
                if not CompanyIdentityValidator.pre_filter(company, c.url):
                    funnel["skipped_validation"] += 1
                    c.inspector_error = "Identity Pre-filter failed (Mismatch)"
                    continue
                    
                if c.score >= policy.min_score or (policy.inspect_even_if_single_candidate and len(valid_candidates) == 1):
                    scored_valid.append(c)
                else:
                    funnel["skipped_score"] += 1
                    
            funnel["score_passed"] = len(scored_valid)
            
            # 5. Cheap Validation
            from src.discovery.pipeline.validators import CandidateValidator
            validator = CandidateValidator(http)
            
            validated_candidates = []
            for c in scored_valid:
                v_start = time.time()
                is_valid = await validator.validate(c)
                c.validator_time_ms = int((time.time() - v_start) * 1000)
                if is_valid:
                    validated_candidates.append(c)
                else:
                    funnel["skipped_validation"] += 1
                    c.inspector_error = "Failed cheap validation"
                    
            funnel["validation_passed"] = len(validated_candidates)
            
            # 6. Budget enforcement
            candidates_to_inspect = validated_candidates[:policy.max_candidates]
            funnel["skipped_budget"] = len(validated_candidates) - len(candidates_to_inspect)
            funnel["inspected"] = len(candidates_to_inspect)
            
            # 7. Parallel Bounded Inspector
            verified_results = []
            sem = asyncio.Semaphore(policy.concurrency)
            
            async def run_inspector(c: Candidate):
                async with sem:
                    for plugin in self.plugins:
                        if plugin.provider_name == c.parsed_identity.ats:
                            inspector = plugin.inspector()
                            i_start = time.time()
                            try:
                                inspection = await inspector.inspect_board(c.url)
                                c.inspector_time_ms = int((time.time() - i_start) * 1000)
                                if inspection.api_verified:
                                    # Post-Inspector Identity Verification
                                    identity_validator = CompanyIdentityValidator(http)
                                    id_res = await identity_validator.validate(company, c.url, inspection)
                                    c.identity_result = id_res
                                    
                                    if id_res.confidence >= 0.3:
                                        c.inspector_success = True
                                        return c
                                    else:
                                        c.inspector_error = f"Identity Verification Failed: {id_res.reason}"
                                        return None
                                else:
                                    c.inspector_error = "API Verification Failed"
                                    return None
                            except Exception as e:
                                c.inspector_time_ms = int((time.time() - i_start) * 1000)
                                c.inspector_error = str(e)
                                return None
                    return None
            
            if candidates_to_inspect:
                tasks = [run_inspector(c) for c in candidates_to_inspect]
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res:
                        verified_results.append(res)
                        
            # BROWSER FALLBACK
            if not verified_results:
                from src.discovery.pipeline.browser_source import BrowserSearchSource
                b_source = BrowserSearchSource()
                try:
                    fallback_res = await b_source.discover(context)
                    fallback_cands = fallback_res.candidates
                    
                    if fallback_cands:
                        scored_candidates.extend(fallback_cands)
                        # Parse
                        for c in fallback_cands:
                            for plugin in self.plugins:
                                identity, conf, reason = plugin.parse_candidate(c.url)
                                if identity:
                                    c.parsed_identity = identity
                                    c.parser_success = True
                                    c.parser_confidence = conf
                                    c.parser_reason = reason
                                    break
                                else:
                                    c.parser_success = False
                                    c.parser_reason = reason
                                    
                        # Filter parsed
                        fallback_cands = [c for c in fallback_cands if c.parser_success]
                        
                        # Pre-filter and score
                        fallback_valid = []
                        for c in fallback_cands:
                            if CompanyIdentityValidator.pre_filter(company, c.url):
                                fallback_valid.append(c)
                                
                        # Cheap Validate
                        fallback_validated = []
                        for c in fallback_valid:
                            if await validator.validate(c):
                                fallback_validated.append(c)
                                
                        # Inspect
                        if fallback_validated:
                            tasks = [run_inspector(c) for c in fallback_validated[:policy.max_candidates]]
                            f_results = await asyncio.gather(*tasks)
                            for res in f_results:
                                if res:
                                    verified_results.append(res)
                except Exception as e:
                    logger.error(f"Browser fallback failed: {e}")
                        
                        
            # PROMOTION TO REGISTRY
            for c in verified_results:
                plugin = next((p for p in self.plugins if p.provider_name == c.parsed_identity.ats), None)
                if plugin:
                    canonical_endpoint = plugin.canonicalize(c.url)
                    endpoint_hash = hashlib.sha256(canonical_endpoint.encode()).hexdigest()
                    
                    vr = VerificationResult(
                        company_id=company_id,
                        company_domain=company_domain,
                        company_name=company,
                        ats_type=c.parsed_identity.ats,
                        endpoint=c.url,
                        canonical_endpoint=canonical_endpoint,
                        endpoint_hash=endpoint_hash,
                        status='ACTIVE',
                        discovery_source="Orchestrator", # Can be extracted from Evidence
                        search_provider=c.search_provider,
                        search_query=c.search_query,
                        search_rank=c.search_rank,
                        identity_score=c.identity_result.confidence if c.identity_result else 0.0,
                        inspector_score=1.0,
                        plugin_name=plugin.__class__.__name__,
                        plugin_version="1.0",
                        ats_metadata=plugin.extract_metadata(c.url) if hasattr(plugin, 'extract_metadata') else "{}"
                    )
                    self.registry.promote_endpoint(company_id, vr)
                        
        return {
            "verified": verified_results,
            "all_candidates": scored_candidates,
            "funnel": funnel,
            "duration": time.time() - start_time
        }
