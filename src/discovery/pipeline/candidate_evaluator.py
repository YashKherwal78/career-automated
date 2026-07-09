"""
CandidateEvaluator — Sprint C1B

Evidence Collection → Scoring → Ranking → Threshold + Max-K Selection

Architecture principle: This module knows nothing about HTTP or ATS APIs.
It operates purely on URLs and metadata already collected by the sources.
The Orchestrator feeds candidates in; this module returns a ranked, pruned list.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urlparse

from src.discovery.pipeline.fallback_models import (
    Candidate, CandidateCategory, CandidateEvidence, DiscoveryPolicy
)

logger = logging.getLogger("CandidateEvaluator")

# ---------------------------------------------------------------------------
# Static knowledge tables
# ---------------------------------------------------------------------------

# Hostnames that unambiguously identify a specific ATS
_DIRECT_ATS_HOSTS: Set[str] = {
    "boards.greenhouse.io",
    "api.greenhouse.io",
    "jobs.lever.co",
    "api.lever.co",
    "jobs.ashbyhq.com",
    "api.ashbyhq.com",
    "apply.workable.com",
    "jobs.smartrecruiters.com",
    "recruiting.myworkdayjobs.com",
    "app.breezy.hr",
    "hire.withgoogle.com",
    "app.teamtailor.com",
    "jobs.jobvite.com",
    "recruitee.com",
    "talent.icims.com",
    "eightfold.ai",
}

# Hostname fragments that indicate a direct ATS hit (for subdomain patterns)
_DIRECT_ATS_FRAGMENTS: List[str] = [
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "smartrecruiters.com",
    "teamtailor.com",
    "breezy.hr",
    "jobvite.com",
    "icims.com",
    "eightfold.ai",
    "bamboohr.com",
    "rippling.com",
]

# Paths that strongly suggest a careers landing page
_CAREERS_PATHS: Set[str] = {"/careers", "/career", "/jobs", "/job"}

# Paths that moderately suggest a careers landing page
_LIKELY_CAREERS_PATHS = re.compile(
    r"/(join[-_]?us|work[-_]?with[-_]?us|open[-_]?roles?|hiring|opportunities|vacancies|positions)",
    re.IGNORECASE
)

# Hostnames that are social / aggregator noise
_SOCIAL_HOSTS: Set[str] = {
    "linkedin.com", "www.linkedin.com",
    "glassdoor.com", "www.glassdoor.com",
    "indeed.com", "www.indeed.com",
    "wellfound.com", "angel.co",
    "twitter.com", "x.com",
    "facebook.com",
}

# Patterns in hostnames or paths that indicate blog/news noise
_BLOG_NEWS_PATTERNS = re.compile(
    r"(techcrunch|venturebeat|crunchbase|medium\.com|substack|forbes|bloomberg|reuters|/blog|/news|/press|/media|/article)",
    re.IGNORECASE
)

# Maximum plausible score for normalization
_MAX_POSSIBLE_SCORE = 100 + 80 + 25 + 20 + 15 + 10  # direct_ats + redirect + hist + fingerprint + robots + sitemap = 250


# ---------------------------------------------------------------------------
# Category detection (pure function — no I/O)
# ---------------------------------------------------------------------------

def _categorize(url: str, ats_domains: List[str]) -> CandidateCategory:
    """Assign a coarse category purely from URL structure. No network calls."""
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        host = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.rstrip("/") or "/"

        # Direct ATS check: exact known hosts
        if host in _DIRECT_ATS_HOSTS:
            return CandidateCategory.DIRECT_ATS
        # Direct ATS check: fragment match (subdomains like {tenant}.myworkdayjobs.com)
        for frag in _DIRECT_ATS_FRAGMENTS:
            if frag in host:
                return CandidateCategory.DIRECT_ATS
        # Caller-supplied ATS domains (from plugins)
        for d in ats_domains:
            if d and d in host:
                return CandidateCategory.DIRECT_ATS

        # Social / aggregator
        if host in _SOCIAL_HOSTS:
            return CandidateCategory.SOCIAL

        # Blog / news
        if _BLOG_NEWS_PATTERNS.search(host) or _BLOG_NEWS_PATTERNS.search(path):
            return CandidateCategory.BLOG_NEWS

        # Careers / jobs landing page
        if path.lower() in _CAREERS_PATHS:
            return CandidateCategory.CAREERS_PAGE if "career" in path.lower() else CandidateCategory.JOBS_PAGE

        # Likely careers
        if _LIKELY_CAREERS_PATHS.search(path):
            return CandidateCategory.LIKELY_CAREERS

        # Homepage
        if path in ("/", ""):
            return CandidateCategory.HOMEPAGE

        return CandidateCategory.UNKNOWN

    except Exception:
        return CandidateCategory.UNKNOWN


# ---------------------------------------------------------------------------
# Evidence collector (attaches a CandidateEvidence to each Candidate)
# ---------------------------------------------------------------------------

def collect_evidence(
    candidate: Candidate,
    ats_domains: List[str],
    historical_verified_urls: Optional[Set[str]] = None,
) -> CandidateEvidence:
    """
    Collects all available structural evidence for a candidate URL.
    This does NOT make network calls — it works on data already in memory.
    Redirect evidence is already embedded in candidate.evidence (from HeadProbeSource).
    """
    url = candidate.url
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        host = parsed.netloc.lower().removeprefix("www.")
    except Exception:
        host = ""

    category = _categorize(url, ats_domains)

    # ATS hostname
    ats_hostname = None
    if category == CandidateCategory.DIRECT_ATS:
        for frag in _DIRECT_ATS_FRAGMENTS:
            if frag in host:
                ats_hostname = host
                break

    # Redirect evidence — HeadProbeSource already annotates redirect candidates.
    # We look for an Evidence entry where description contains "Redirect".
    redirect_target = None
    redirect_is_ats = False
    for ev in candidate.evidence:
        if "Redirect" in ev.description:
            redirect_is_ats = ev.weight >= 40  # HeadProbe sets weight=40 for ATS redirects

    # ATS fingerprint on page — StaticLandingPageSource sets weight ≥ 40
    ats_fingerprint_on_page = any(
        ev.weight >= 40 and "ATS" in ev.description
        for ev in candidate.evidence
    )

    # Historical verification
    historical_verified = (
        url in historical_verified_urls
        if historical_verified_urls else False
    )

    return CandidateEvidence(
        source="CandidateEvaluator",
        category=category,
        ats_hostname=ats_hostname,
        ats_fingerprint_on_page=ats_fingerprint_on_page,
        redirect_target=redirect_target,
        redirect_is_ats=redirect_is_ats,
        historical_verified=historical_verified,
    )


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def score_candidate(evidence: CandidateEvidence, policy: DiscoveryPolicy) -> int:
    """
    Produces a single integer score and populates evidence.score_breakdown
    so every point is traceable back to a named signal.
    """
    bd: dict[str, int] = {}

    cat = evidence.category
    if cat == CandidateCategory.DIRECT_ATS:
        bd["direct_ats"] = policy.direct_ats_bonus
    elif cat == CandidateCategory.CAREERS_PAGE:
        bd["careers_path"] = policy.careers_page_bonus
    elif cat == CandidateCategory.JOBS_PAGE:
        bd["jobs_path"] = policy.jobs_page_bonus
    elif cat == CandidateCategory.LIKELY_CAREERS:
        bd["likely_careers_path"] = policy.likely_careers_bonus
    elif cat == CandidateCategory.HOMEPAGE:
        bd["homepage"] = policy.homepage_bonus
    elif cat == CandidateCategory.SOCIAL:
        bd["social_penalty"] = policy.social_penalty
    elif cat == CandidateCategory.BLOG_NEWS:
        bd["blog_news_penalty"] = policy.blog_penalty
    else:
        bd["unknown_penalty"] = policy.unknown_penalty

    if evidence.ats_fingerprint_on_page:
        bd["ats_fingerprint"] = policy.ats_fingerprint_bonus
    if evidence.robots_mentions_jobs:
        bd["robots_signal"] = policy.robots_bonus
    if evidence.sitemap_has_jobs:
        bd["sitemap_signal"] = policy.sitemap_bonus
    if evidence.redirect_is_ats:
        bd["redirect_to_ats"] = policy.redirect_ats_bonus
    if evidence.historical_verified:
        bd["historical_success"] = policy.historical_bonus

    evidence.score_breakdown = bd
    return sum(bd.values())


# ---------------------------------------------------------------------------
# Public entry point: rank_candidates
# ---------------------------------------------------------------------------

@dataclass
class RankedCandidate:
    candidate: Candidate
    evidence: CandidateEvidence
    raw_score: int
    normalized_score: float          # raw_score / _MAX_POSSIBLE_SCORE, clamped [0, 1]
    selected_for_inspection: bool = False
    skip_reason: Optional[str] = None

    def explain(self) -> str:
        """Human-readable explanation suitable for Mission Control telemetry."""
        lines = [f"Candidate: {self.candidate.url}", f"Category: {self.evidence.category.value}",
                 f"Score: {self.raw_score} (normalized {self.normalized_score:.2f})", "Breakdown:"]
        for label, pts in self.evidence.score_breakdown.items():
            sign = "+" if pts >= 0 else ""
            lines.append(f"  {sign}{pts:4d}  {label}")
        lines.append(f"Selected for inspection: {self.selected_for_inspection}")
        if self.skip_reason:
            lines.append(f"Skip reason: {self.skip_reason}")
        return "\n".join(lines)


def rank_candidates(
    candidates: List[Candidate],
    ats_domains: List[str],
    policy: Optional[DiscoveryPolicy] = None,
    historical_verified_urls: Optional[Set[str]] = None,
) -> List[RankedCandidate]:
    """
    Full pipeline: Evidence → Score → Rank → Threshold + Max-K gate.

    Returns ALL candidates (including rejected ones) with selection flags set.
    Caller can log / telemetry the full list for observability.
    """
    if policy is None:
        policy = DiscoveryPolicy()

    ranked: List[RankedCandidate] = []
    for c in candidates:
        ev = collect_evidence(c, ats_domains, historical_verified_urls)
        raw = score_candidate(ev, policy)
        norm = max(0.0, min(1.0, raw / _MAX_POSSIBLE_SCORE))
        ranked.append(RankedCandidate(candidate=c, evidence=ev, raw_score=raw, normalized_score=norm))

    # Sort descending by raw score
    ranked.sort(key=lambda r: r.raw_score, reverse=True)

    # Apply Threshold + Max-K selection
    selected = 0
    prev_norm: Optional[float] = None

    for r in ranked:
        if selected >= policy.max_k:
            r.skip_reason = f"max_k={policy.max_k} reached"
            continue

        if r.normalized_score < policy.min_confidence_threshold:
            r.skip_reason = f"score {r.normalized_score:.2f} < threshold {policy.min_confidence_threshold}"
            continue

        if prev_norm is not None:
            gap = prev_norm - r.normalized_score
            if gap >= policy.confidence_gap_stop:
                r.skip_reason = f"confidence gap {gap:.2f} >= stop threshold {policy.confidence_gap_stop}"
                continue

        r.selected_for_inspection = True
        prev_norm = r.normalized_score
        selected += 1

    logger.debug(
        "rank_candidates: %d input → %d selected (policy: max_k=%d, threshold=%.2f)",
        len(ranked), selected, policy.max_k, policy.min_confidence_threshold
    )
    return ranked
