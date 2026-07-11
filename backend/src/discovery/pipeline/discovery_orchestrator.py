import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Set

from src.discovery.pipeline.fallback_models import (
    DiscoveryBudget, Evidence, Candidate, DiscoverySource, DiscoveryPlugin, VerificationPolicy,
    VerificationResult, DiscoveryPolicy
)
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.pipeline.caches import ReplayCache
from src.discovery.pipeline.url_canonicalizer import URLCanonicalizer
from src.discovery.pipeline.ats_registry import ATSRegistry
from src.discovery.pipeline.candidate_evaluator import rank_candidates
from src.discovery.pipeline.landing_page_resolver import LandingPageResolver
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

    async def execute(self, company: str, website: str, budget: DiscoveryBudget, run_id: Optional[str] = None, company_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # Telemetry Setup
        from src.discovery.pipeline.telemetry import Telemetry, Stage, Status, ReasonCode
        if not run_id:
            run_id = f"orchestrator-run-{int(time.time())}"
        
        from urllib.parse import urlparse
        parsed = urlparse(website if website.startswith('http') else f"https://{website}")
        company_domain = parsed.netloc.replace('www.', '')
        if not company_id:
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
                        # Step 1: Generic URL normalization (tracking params, trailing slashes, etc.)
                        canonical_url = URLCanonicalizer.canonicalize(c.url)

                        # Step 2: Plugin-owned ATS canonicalization.
                        # Each plugin knows its own URL structure (board vs job-level paths).
                        # The first plugin that recognizes the URL collapses it to board-level.
                        # This prevents job-level URLs (e.g. jobs.ashbyhq.com/Co/{uuid}) from
                        # inflating the candidate pool with duplicates of the same board.
                        for plugin in self.plugins:
                            identity, _conf, _reason = plugin.parse_candidate(canonical_url)
                            if identity:
                                canonical_url = plugin.canonicalize(canonical_url)
                                break

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

            # Emit URL collection telemetry
            Telemetry.record_event(
                stage=Stage.URL_COLLECTED,
                status=Status.SUCCESS,
                run_id=run_id,
                company_id=company_id,
                worker_name="EndpointVerificationWorker",
                metadata={"raw_candidates_found": len(candidate_pool)}
            )

            scored_candidates = list(candidate_pool.values())

            # -------------------------------------------------------------------
            # 2. Homepage fetch for ATS penalty scoring (unchanged)
            # -------------------------------------------------------------------
            try:
                h_start = time.time()
                res = await http.fetch('GET', website)
                h_latency = int((time.time() - h_start) * 1000)
                if res and res.payload:
                    self._apply_known_ats_penalties(scored_candidates, res.payload.decode('utf-8', errors='ignore'))
                    Telemetry.record_event(stage=Stage.HOMEPAGE_FETCH, status=Status.SUCCESS, run_id=run_id,
                        company_id=company_id, worker_name="EndpointVerificationWorker",
                        latency_ms=h_latency, reason_code=ReasonCode.NONE)
                else:
                    Telemetry.record_event(stage=Stage.HOMEPAGE_FETCH, status=Status.FAILURE, run_id=run_id,
                        company_id=company_id, worker_name="EndpointVerificationWorker",
                        latency_ms=h_latency, reason_code=ReasonCode.NO_CAREERS_PAGE)
            except Exception as e:
                h_latency = int((time.time() - h_start) * 1000)
                Telemetry.record_event(stage=Stage.HOMEPAGE_FETCH, status=Status.FAILURE, run_id=run_id,
                    company_id=company_id, worker_name="EndpointVerificationWorker",
                    latency_ms=h_latency, reason_code=ReasonCode.NETWORK_TIMEOUT,
                    metadata={"error": str(e)})

            # -------------------------------------------------------------------
            # 3. Evidence Collection → Scoring → Rank → Threshold + Max-K gate
            # (C1B: CandidateEvaluator replaces the old immediate-drop parser loop)
            # -------------------------------------------------------------------
            discovery_policy = self.discovery_policy if hasattr(self, 'discovery_policy') else DiscoveryPolicy()

            # Pull historical verified URLs from the registry for bonus scoring
            historical_urls: Set[str] = set()
            try:
                historical_urls = self.registry.get_all_active_endpoints_for_domain(company_domain)
            except Exception:
                pass

            ranked = rank_candidates(
                candidates=scored_candidates,
                ats_domains=self.ats_domains,
                policy=discovery_policy,
                historical_verified_urls=historical_urls,
            )

            # Emit per-candidate evaluation telemetry
            for r in ranked:
                Telemetry.record_event(
                    stage=Stage.CANDIDATE_CREATED,
                    status=Status.SUCCESS if r.selected_for_inspection else Status.FAILURE,
                    run_id=run_id,
                    company_id=company_id,
                    candidate_url=r.candidate.url,
                    worker_name="EndpointVerificationWorker",
                    metadata={
                        "category": r.evidence.category.value,
                        "raw_score": r.raw_score,
                        "normalized_score": round(r.normalized_score, 3),
                        "selected": r.selected_for_inspection,
                        "skip_reason": r.skip_reason,
                        "score_breakdown": r.evidence.score_breakdown,
                        "explanation": r.explain(),
                        # C1B.6: Decision replay fields
                        "pipeline_stage": "CANDIDATE_RANKING",
                        "final_reason_code": (
                            "SELECTED" if r.selected_for_inspection
                            else ("MAX_K_EXCEEDED" if r.skip_reason and "max_k" in r.skip_reason
                                  else ("CONFIDENCE_GAP" if r.skip_reason and "gap" in r.skip_reason
                                        else ("BELOW_THRESHOLD" if r.skip_reason and "threshold" in r.skip_reason
                                              else "UNKNOWN")))
                        ),
                    }
                )

            selected_ranked = [r for r in ranked if r.selected_for_inspection]

            funnel = {
                "generated": len(scored_candidates),
                "ranked": len(ranked),
                "selected_for_inspection": len(selected_ranked),
                "rejected_threshold": sum(1 for r in ranked if not r.selected_for_inspection and r.skip_reason and "threshold" in r.skip_reason),
                "rejected_gap": sum(1 for r in ranked if not r.selected_for_inspection and r.skip_reason and "gap" in r.skip_reason),
                "rejected_max_k": sum(1 for r in ranked if not r.selected_for_inspection and r.skip_reason and "max_k" in r.skip_reason),
                # legacy keys kept for backward compat with existing monitoring
                "parsed": len(selected_ranked),
                "score_passed": len(selected_ranked),
                "validation_passed": 0,
                "inspected": 0,
                "skipped_score": sum(1 for r in ranked if not r.selected_for_inspection),
                "skipped_validation": 0,
                "skipped_budget": 0,
            }

            # -------------------------------------------------------------------
            # 4. LandingPageResolver + ATS Parser
            # Generic /careers pages go through the resolver first; Direct ATS
            # URLs skip straight to the plugin parser.
            # -------------------------------------------------------------------
            policy = self.verification_policy if hasattr(self, 'verification_policy') else VerificationPolicy()
            from src.discovery.pipeline.identity_validator import CompanyIdentityValidator
            from src.discovery.pipeline.validators import CandidateValidator

            resolver = LandingPageResolver(http)
            validator = CandidateValidator(http)
            valid_candidates = []

            for r in selected_ranked:
                c = r.candidate
                from src.discovery.pipeline.fallback_models import CandidateCategory

                # --- Direct ATS: parse immediately, no resolver needed ---
                if r.evidence.category == CandidateCategory.DIRECT_ATS:
                    for plugin in self.plugins:
                        identity, conf, reason = plugin.parse_candidate(c.url)
                        if identity:
                            c_copy = Candidate(url=c.url, evidence=list(c.evidence))
                            c_copy.parsed_identity = identity
                            c_copy.parser_success = True
                            c_copy.parser_confidence = conf
                            c_copy.parser_reason = reason
                            for attr in ('search_provider', 'search_query', 'search_rank', 'search_title'):
                                if hasattr(c, attr): setattr(c_copy, attr, getattr(c, attr))
                            valid_candidates.append(c_copy)
                            break
                    continue

                # --- Generic careers page: run LandingPageResolver first ---
                resolved = await resolver.resolve(c.url)
                if resolved.success:
                    c.url = resolved.resolved_url  # swap to the ATS URL
                    for plugin in self.plugins:
                        identity, conf, reason = plugin.parse_candidate(c.url)
                        if identity:
                            c_copy = Candidate(url=c.url, evidence=list(c.evidence))
                            c_copy.parsed_identity = identity
                            c_copy.parser_success = True
                            c_copy.parser_confidence = conf * resolved.confidence  # compound confidence
                            c_copy.parser_reason = reason
                            for attr in ('search_provider', 'search_query', 'search_rank', 'search_title'):
                                if hasattr(c, attr): setattr(c_copy, attr, getattr(c, attr))
                            valid_candidates.append(c_copy)
                            break
                else:
                    logger.debug("LandingPageResolver failed for %s: %s", c.url, resolved.error)

            funnel["validation_passed"] = len(valid_candidates)

            # -------------------------------------------------------------------
            # 5. Identity Pre-filter
            # -------------------------------------------------------------------
            scored_valid = []
            for c in valid_candidates:
                if not CompanyIdentityValidator.pre_filter(company, c.url):
                    funnel["skipped_validation"] += 1
                    c.inspector_error = "Identity Pre-filter failed"
                    continue
                scored_valid.append(c)

            funnel["score_passed"] = len(scored_valid)

            # -------------------------------------------------------------------
            # 6. Cheap HTTP validation
            # -------------------------------------------------------------------
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

            candidates_to_inspect = validated_candidates  # already gated by Max-K above
            funnel["inspected"] = len(candidates_to_inspect)

            # -------------------------------------------------------------------
            # 7. Parallel bounded ATS Inspector (unchanged)
            # -------------------------------------------------------------------
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
                                        Telemetry.record_event(
                                            stage=Stage.INSPECTOR_EXECUTED,
                                            status=Status.SUCCESS,
                                            run_id=run_id,
                                            company_id=company_id,
                                            candidate_url=c.url,
                                            worker_name="EndpointVerificationWorker",
                                            ats_type=c.parsed_identity.ats,
                                            plugin=plugin.provider_name,
                                            latency_ms=c.inspector_time_ms,
                                            reason_code=ReasonCode.NONE
                                        )
                                        return c
                                    else:
                                        c.inspector_error = f"Identity Verification Failed: {id_res.reason}"
                                        Telemetry.record_event(
                                            stage=Stage.INSPECTOR_EXECUTED,
                                            status=Status.FAILURE,
                                            run_id=run_id,
                                            company_id=company_id,
                                            candidate_url=c.url,
                                            worker_name="EndpointVerificationWorker",
                                            ats_type=c.parsed_identity.ats,
                                            plugin=plugin.provider_name,
                                            latency_ms=c.inspector_time_ms,
                                            reason_code=ReasonCode.INSPECTOR_FAILED,
                                            metadata={"error": c.inspector_error}
                                        )
                                        return None
                                else:
                                    c.inspector_error = "API Verification Failed"
                                    Telemetry.record_event(
                                        stage=Stage.INSPECTOR_EXECUTED,
                                        status=Status.FAILURE,
                                        run_id=run_id,
                                        company_id=company_id,
                                        candidate_url=c.url,
                                        worker_name="EndpointVerificationWorker",
                                        ats_type=c.parsed_identity.ats,
                                        plugin=plugin.provider_name,
                                        latency_ms=c.inspector_time_ms,
                                        reason_code=ReasonCode.INSPECTOR_FAILED,
                                        metadata={"error": c.inspector_error}
                                    )
                                    return None
                            except Exception as e:
                                c.inspector_time_ms = int((time.time() - i_start) * 1000)
                                c.inspector_error = str(e)
                                Telemetry.record_event(
                                    stage=Stage.INSPECTOR_EXECUTED,
                                    status=Status.FAILURE,
                                    run_id=run_id,
                                    company_id=company_id,
                                    candidate_url=c.url,
                                    worker_name="EndpointVerificationWorker",
                                    ats_type=c.parsed_identity.ats,
                                    plugin=plugin.provider_name,
                                    latency_ms=c.inspector_time_ms,
                                    reason_code=ReasonCode.INSPECTOR_FAILED,
                                    metadata={"error": c.inspector_error}
                                )
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
                    
                    Telemetry.record_event(
                        stage=Stage.ENDPOINT_PROMOTED,
                        status=Status.SUCCESS,
                        run_id=run_id,
                        company_id=company_id,
                        candidate_url=c.url,
                        worker_name="EndpointVerificationWorker",
                        ats_type=c.parsed_identity.ats,
                        plugin=plugin.provider_name,
                        metadata={"canonical_endpoint": canonical_endpoint}
                    )
                        
        return {
            "verified": verified_results,
            "all_candidates": scored_candidates,
            "funnel": funnel,
            "duration": time.time() - start_time
        }
