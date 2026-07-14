import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class EndpointCandidatePayload:
    def __init__(self, provider_id: str, url: str, discovery_source: str, evidence: Dict[str, Any], confidence_score: int):
        self.provider_id = provider_id
        self.url = url
        self.discovery_source = discovery_source
        self.evidence = evidence
        self.confidence_score = confidence_score

class DiscoveryProvider(ABC):
    @abstractmethod
    def discover(self, company_payload: Dict[str, Any]) -> List[EndpointCandidatePayload]:
        pass

class KnownDatasetDiscoverer(DiscoveryProvider):
    """Generates candidates from known dataset mappings (e.g. from the benchmark CSV)."""
    
    def discover(self, company_payload: Dict[str, Any]) -> List[EndpointCandidatePayload]:
        candidates = []
        metadata = company_payload.get("metadata", {})
        
        if metadata.get("source") == "jobhive":
            ats_slug = metadata.get("ats_slug")
            provider = metadata.get("known_ats")
            if ats_slug and provider:
                # Derive possible URL
                url = metadata.get("board_url", "")
                candidates.append(EndpointCandidatePayload(
                    provider_id=provider,
                    url=url,
                    discovery_source="EXISTING_DATASET",
                    evidence={"source": "jobhive", "slug": ats_slug},
                    confidence_score=90
                ))
        return candidates

class RegexDiscoverer(DiscoveryProvider):
    """Generates candidates by guessing common ATS subdomains for the company."""
    
    def discover(self, company_payload: Dict[str, Any]) -> List[EndpointCandidatePayload]:
        candidates = []
        domain = company_payload.get("domain", "")
        if not domain:
            return candidates
            
        slug = domain.split('.')[0]
        
        # Greenhouse
        candidates.append(EndpointCandidatePayload(
            provider_id="greenhouse",
            url=f"https://boards.greenhouse.io/{slug}",
            discovery_source="REGEX",
            evidence={"pattern": "boards.greenhouse.io/{slug}"},
            confidence_score=40
        ))
        
        # Lever
        candidates.append(EndpointCandidatePayload(
            provider_id="lever",
            url=f"https://jobs.lever.co/{slug}",
            discovery_source="REGEX",
            evidence={"pattern": "jobs.lever.co/{slug}"},
            confidence_score=40
        ))
        
        # Ashby
        candidates.append(EndpointCandidatePayload(
            provider_id="ashby",
            url=f"https://jobs.ashbyhq.com/{slug}",
            discovery_source="REGEX",
            evidence={"pattern": "jobs.ashbyhq.com/{slug}"},
            confidence_score=40
        ))
        
        return candidates

class DiscoveryRegistry:
    _providers = [
        KnownDatasetDiscoverer(),
        RegexDiscoverer()
    ]
    
    @classmethod
    def run_all(cls, company_payload: Dict[str, Any]) -> List[EndpointCandidatePayload]:
        all_candidates = []
        for provider in cls._providers:
            all_candidates.extend(provider.discover(company_payload))
        return all_candidates
