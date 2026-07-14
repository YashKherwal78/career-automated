from typing import List
import time
from urllib.parse import urlparse, urljoin
from src.discovery.pipeline.fallback_models import DiscoverySource, Candidate, Evidence, SourceResult, StageTrace, ProbeResult
from src.discovery.pipeline.discovery_orchestrator import DiscoveryContext

class HeadProbeSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        start_time = time.time()
        probes = [
            "/",
            "/careers",
            "/jobs",
            "/careers/jobs",
            "/join-us",
            "/work-with-us",
            "/careers/search",
            "/careers/job-search",
            "/company/careers",
            "/about/careers"
        ]
        
        candidates = []
        probe_results = []
        redirect_chains = []
        
        sem = asyncio.Semaphore(5)
        
        async def run_probe(path: str):
            url = urljoin(context.website, path)
            probe_start = time.time()
            async with sem:
                try:
                    # Enforce a short 3-second timeout for head probes
                    # For compatibility we can just use asyncio.wait_for, but HttpClient might not respect it safely if session gets stuck.
                    # aiohttp session can take `timeout` in request if we pass it.
                    # Our context.fetch accepts **kwargs.
                    import aiohttp
                    res = await context.head(url, timeout=aiohttp.ClientTimeout(total=3.0))
                    duration = int((time.time() - probe_start) * 1000)
                    
                    redirect_count = len(res.redirect_chain) - 1 if res.redirect_chain else 0
                    
                    probe_res = ProbeResult(
                        path=path,
                        status=res.status_code,
                        final_url=res.final_url,
                        latency_ms=duration,
                        redirect_count=redirect_count,
                        success=True
                    )
                    
                    evidence_list = []
                    c_out = None
                    
                    if redirect_count > 0:
                        evidence_list = [Evidence(source="HeadProbe", weight=5, description="Redirect occurred")]
                        
                        parsed_final = urlparse(res.final_url)
                        final_netloc = parsed_final.netloc.lower()
                        
                        if any(ats_domain in final_netloc for ats_domain in context.ats_domains):
                            evidence_list.append(Evidence(source="HeadProbe", weight=40, description="Redirected to known ATS domain"))
                        elif "careers" in final_netloc or "jobs" in final_netloc:
                            evidence_list.append(Evidence(source="HeadProbe", weight=8, description="Redirected to careers subdomain"))
                            
                        c_out = Candidate(url=res.final_url, evidence=evidence_list)
                    elif res.status_code == 200:
                        # Ensure 200 OK active paths (like /jobs) are scraped by StaticLandingPageSource
                        evidence_list = [Evidence(source="HeadProbe", weight=2, description="Active 200 OK path")]
                        c_out = Candidate(url=res.final_url, evidence=evidence_list)
                        
                    return probe_res, c_out, res.redirect_chain if redirect_count > 0 else None
                        
                except Exception as e:
                    print(f"Exception in HeadProbeSource for {path}: {repr(e)}")
                    duration = int((time.time() - probe_start) * 1000)
                    return ProbeResult(
                        path=path,
                        status=0,
                        final_url="",
                        latency_ms=duration,
                        redirect_count=0,
                        success=False
                    ), None, None
                    
        tasks = [run_probe(p) for p in probes]
        results = await asyncio.gather(*tasks)
        
        for p_res, c_out, r_chain in results:
            probe_results.append(p_res)
            if c_out:
                candidates.append(c_out)
            if r_chain:
                redirect_chains.append(r_chain)

        trace = StageTrace(
            stage="head_probe",
            success=True, # We do not fail the trace even if all probes 404/405
            duration_ms=int((time.time() - start_time) * 1000),
            requests=context.requests_used,
            candidates_found=len(candidates),
            evidence=[],
            urls=[c.url for c in candidates],
            probe_results=probe_results,
            redirect_chains=redirect_chains
        )
        
        return SourceResult(
            candidates=candidates,
            trace=trace,
            requests_used=context.requests_used,
            bytes_downloaded=context.bytes_downloaded
        )

import re

class StaticLandingPageSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        start_time = time.time()
        candidates = []
        probe_results = []
        
        # We fetch the original website + any 200 OK observations from HeadProbe
        # Since HeadProbe doesn't explicitly save "observations" yet, we'll fetch context.website
        # and any candidate URLs found so far that aren't already identified as ATS.
        urls_to_fetch = [context.website]
        for c in context.candidate_pool:
            urls_to_fetch.append(c.url)
            
        urls_to_fetch = list(set(urls_to_fetch))
        
        for url in urls_to_fetch:
            probe_start = time.time()
            try:
                res = await context.fetch('GET', url)
                duration = int((time.time() - probe_start) * 1000)
                
                probe_res = ProbeResult(
                    path=url,
                    status=res.status_code,
                    final_url=res.final_url,
                    latency_ms=duration,
                    redirect_count=len(res.redirect_chain)-1 if res.redirect_chain else 0,
                    success=res.status_code == 200
                )
                probe_results.append(probe_res)
                
                if res.status_code == 200 and res.payload:
                    content = res.payload.decode('utf-8', errors='ignore')
                    
                    found_urls = set()
                    
                    # Layer 1: HTML tags
                    hrefs = re.findall(r'href=["\'](https?://[^"\']+)["\']', content)
                    srcs = re.findall(r'src=["\'](https?://[^"\']+)["\']', content)
                    found_urls.update(hrefs)
                    found_urls.update(srcs)
                    
                    # Layer 3: Regex over the entire response body for known ATS signatures
                    ats_signatures = [
                        r'https?://[a-zA-Z0-9.-]+\.myworkdayjobs\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.apply\.workday\.com[^"\'\\\s]*',
                        r'https?://boards\.greenhouse\.io[^"\'\\\s]*',
                        r'https?://jobs\.lever\.co[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.ashbyhq\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.workable\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.smartrecruiters\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.teamtailor\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.breezy\.hr[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.recruitee\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.jobvite\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.eightfold\.ai[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.phenom\.com[^"\'\\\s]*',
                        r'https?://[a-zA-Z0-9.-]+\.icims\.com[^"\'\\\s]*'
                    ]
                    
                    for sig in ats_signatures:
                        matches = re.findall(sig, content)
                        found_urls.update(matches)
                        
                    for found_url in found_urls:
                        # Additive scoring
                        evidence_list = []
                        parsed_url = urlparse(found_url)
                        netloc = parsed_url.netloc.lower()
                        
                        if any(ats in netloc for ats in context.ats_domains):
                            evidence_list.append(Evidence(source="StaticLandingPage", weight=40, description="Extracted known ATS domain"))
                        
                        if evidence_list: # Only emit if it's ATS related for now to avoid explosion of candidates
                            candidates.append(Candidate(url=found_url, evidence=evidence_list))
                            
            except Exception as e:
                probe_results.append(ProbeResult(
                    path=url,
                    status=0,
                    final_url="",
                    latency_ms=int((time.time() - probe_start) * 1000),
                    redirect_count=0,
                    success=False
                ))

        trace = StageTrace(
            stage="static_landing_page",
            success=True,
            duration_ms=int((time.time() - start_time) * 1000),
            requests=context.requests_used,
            candidates_found=len(candidates),
            evidence=[],
            urls=[c.url for c in candidates],
            probe_results=probe_results,
            redirect_chains=[]
        )
        
        return SourceResult(
            candidates=candidates,
            trace=trace,
            requests_used=context.requests_used,
            bytes_downloaded=context.bytes_downloaded
        )
class OSINTSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        return SourceResult(candidates=[], trace=StageTrace(stage="osint", success=True, duration_ms=0, requests=0, candidates_found=0, evidence=[], urls=[]), requests_used=0, bytes_downloaded=0)

class HTMLFingerprintSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        return SourceResult(candidates=[], trace=StageTrace(stage="html", success=True, duration_ms=0, requests=0, candidates_found=0, evidence=[], urls=[]), requests_used=0, bytes_downloaded=0)

class JSFingerprintSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        return SourceResult(candidates=[], trace=StageTrace(stage="js", success=True, duration_ms=0, requests=0, candidates_found=0, evidence=[], urls=[]), requests_used=0, bytes_downloaded=0)

class HeaderSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        return SourceResult(candidates=[], trace=StageTrace(stage="header", success=True, duration_ms=0, requests=0, candidates_found=0, evidence=[], urls=[]), requests_used=0, bytes_downloaded=0)

class SitemapSource(DiscoverySource):
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        return SourceResult(candidates=[], trace=StageTrace(stage="sitemap", success=True, duration_ms=0, requests=0, candidates_found=0, evidence=[], urls=[]), requests_used=0, bytes_downloaded=0)

from duckduckgo_search import DDGS
import asyncio
import random
import json
import os
from src.discovery.search.provider_manager import SearchManager

class ExternalSearchSource(DiscoverySource):
    def __init__(self):
        self.search_manager = SearchManager()

    async def discover(self, context: DiscoveryContext) -> SourceResult:
        start_time = time.time()
        candidates = []
        probe_results = []
        error_msg = None
        
        company = context.company
        parsed_web = urlparse(context.website)
        domain = parsed_web.netloc.lower() or parsed_web.path.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        queries = [
            f'"{company}" careers',
            f'"{company}" jobs',
            f'site:{domain}',
            f'"{company}" Greenhouse',
            f'"{company}" Lever',
            f'"{company}" Ashby',
            f'"{company}" Workable',
            f'"{company}" SmartRecruiters',
            f'"{company}" Teamtailor',
            f'"{company}" Jobvite',
            f'"{company}" BreezyHR',
            f'"{company}" Recruitee'
        ]
        
        try:
            for query in queries:
                if context.search_queries_used >= context.budget.max_search_queries:
                    break
                
                context.search_queries_used += 1
                probe_start = time.time()
                
                results = await self.search_manager.execute_search(query, limit=10)
                
                duration = int((time.time() - probe_start) * 1000)
                
                probe_results.append(ProbeResult(
                    path=query,
                    status=200,
                    final_url="",
                    latency_ms=duration,
                    redirect_count=0,
                    success=True
                ))
                
                for r in results:
                    url = r.url
                    if url:
                        evidence_list = []
                        parsed_url = urlparse(url)
                        netloc = parsed_url.netloc.lower()
                        
                        evidence_list.append(Evidence(source="ExaSource", weight=15, description=f"Found via {r.provider} (Rank {r.rank}): {query}"))
                        if any(ats in netloc for ats in context.ats_domains):
                            evidence_list.append(Evidence(source="ExaSource", weight=40, description=f"{r.provider} returned known ATS domain"))
                        
                        c = Candidate(url=url, evidence=evidence_list)
                        c.search_provider = r.provider
                        c.search_query = query
                        c.search_rank = r.rank
                        c.search_title = r.title
                        candidates.append(c)
        except Exception as e:
            error_msg = str(e)
                    
        trace = StageTrace(
            stage="external_search",
            success=error_msg is None,
            duration_ms=int((time.time() - start_time) * 1000),
            requests=context.requests_used,
            candidates_found=len(candidates),
            evidence=[],
            urls=[c.url for c in candidates],
            probe_results=probe_results,
            redirect_chains=[],
            error=error_msg
        )
        
        return SourceResult(
            candidates=candidates,
            trace=trace,
            requests_used=0,
            bytes_downloaded=0
        )
import urllib.parse
from typing import List, Dict, Any
from src.discovery.pipeline.fallback_models import Candidate, Evidence, DiscoveryBudget
from src.discovery.pipeline.sources import DiscoverySource

class HeuristicTokenSource(DiscoverySource):
    """Generates fallback candidates based on the domain name."""
    
    async def fetch_evidence(self, company: str, website: str, budget: DiscoveryBudget, **kwargs) -> List[Candidate]:
        candidates = []
        try:
            parsed = urllib.parse.urlparse(website)
            domain = parsed.netloc.replace('www.', '')
            token = domain.split('.')[0]
            
            # Known ATS url templates
            ats_templates = [
                ("greenhouse", f"https://boards.greenhouse.io/{token}"),
                ("lever", f"https://jobs.lever.co/{token}"),
                ("ashby", f"https://jobs.ashbyhq.com/{token}"),
                ("workday", f"https://{token}.myworkdayjobs.com/en-US/careers"),
                ("workable", f"https://apply.workable.com/{token}"),
                ("smartrecruiters", f"https://careers.smartrecruiters.com/{token}"),
                ("teamtailor", f"https://careers.{token}.com"),
                ("breezy", f"https://{token}.breezy.hr")
            ]
            
            for provider_id, url in ats_templates:
                candidates.append(Candidate(
                    url=url,
                    evidence=[Evidence(source="HeuristicTokenSource", weight=1, description="Generated from domain heuristic")]
                ))
                
        except Exception:
            pass
            
        return candidates
