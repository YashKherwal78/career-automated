from typing import List, Dict, Any
import datetime
from src.discovery.providers.base_provider import StandardJob

class DiscoveryNormalizer:
    """
    Transforms raw payloads from connectors into standardized Opportunity (StandardJob) objects.
    This decouples data collection from data normalization.
    """
    
    @staticmethod
    def normalize_linkedin(raw_payload: List[Dict[str, Any]]) -> List[StandardJob]:
        normalized = []
        for item in raw_payload:
            normalized.append(StandardJob(
                role=item.get('title', 'Unknown Role'),
                company=item.get('companyName', 'Unknown Company'),
                location=item.get('location', 'Unknown'),
                remote_hybrid_onsite=item.get('workplaceTypes', ['Unknown'])[0] if item.get('workplaceTypes') else 'Unknown',
                experience_required='Unknown',
                skills=[],
                job_description=item.get('description', ''),
                application_url=item.get('url', ''),
                ats_type='linkedin',
                source='LinkedIn',
                date_posted=item.get('postedAt', datetime.datetime.now().isoformat())
            ))
        return normalized

    @staticmethod
    def normalize_greenhouse(raw_payload: List[Dict[str, Any]], company: str) -> List[StandardJob]:
        normalized = []
        for item in raw_payload:
            normalized.append(StandardJob(
                role=item.get('title', 'Unknown Role'),
                company=company,
                location=item.get('location', {}).get('name', 'Unknown'),
                remote_hybrid_onsite='Unknown',
                experience_required='Unknown',
                skills=[],
                job_description='',
                application_url=item.get('absolute_url', ''),
                ats_type='greenhouse',
                source='Greenhouse',
                date_posted=item.get('updated_at', datetime.datetime.now().isoformat())
            ))
        return normalized

    @staticmethod
    def normalize_lever(raw_payload: List[Dict[str, Any]], company: str) -> List[StandardJob]:
        normalized = []
        for item in raw_payload:
            normalized.append(StandardJob(
                role=item.get('text', 'Unknown Role'),
                company=company,
                location=item.get('categories', {}).get('location', 'Unknown'),
                remote_hybrid_onsite=item.get('workplaceType', 'Unknown'),
                experience_required='Unknown',
                skills=[],
                job_description=item.get('descriptionPlain', ''),
                application_url=item.get('hostedUrl', ''),
                ats_type='lever',
                source='Lever',
                date_posted=datetime.datetime.now().isoformat()
            ))
        return normalized
    
    @staticmethod
    def normalize(connector_name: str, raw_payload: List[Any], **kwargs) -> List[StandardJob]:
        if "linkedin" in connector_name.lower():
            return DiscoveryNormalizer.normalize_linkedin(raw_payload)
        elif "greenhouse" in connector_name.lower():
            return DiscoveryNormalizer.normalize_greenhouse(raw_payload, kwargs.get('company', 'Unknown'))
        elif "lever" in connector_name.lower():
            return DiscoveryNormalizer.normalize_lever(raw_payload, kwargs.get('company', 'Unknown'))
        
        # Fallback raw pass-through if already StandardJob
        if raw_payload and isinstance(raw_payload[0], StandardJob):
            return raw_payload
            
        print(f"Normalizer warning: Unknown connector {connector_name}. Returning empty list.")
        return []
