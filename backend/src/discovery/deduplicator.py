from typing import List, Dict, Any

class DiscoveryDeduplicator:
    """
    Deduplicates Opportunities by merging alternative apply sources rather than deleting them.
    Ensures the highest confidence connector becomes the Primary Apply Source.
    """

    @staticmethod
    def deduplicate(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups opportunities by Company and Job Title (or some strong similarity).
        Merges duplicates, picking the highest confidence source as primary.
        """
        unique_jobs: Dict[str, Dict[str, Any]] = {}

        for job in opportunities:
            # Create a simple unique key. In a real system, this might use fuzzy matching.
            key = f"{job.get('company_name', '').lower()}_{job.get('job_title', '').lower()}"
            
            if key not in unique_jobs:
                job['alternative_apply_sources'] = []
                unique_jobs[key] = job
            else:
                existing = unique_jobs[key]
                new_conf = job.get('confidence', 50)
                existing_conf = existing.get('confidence', 50)

                # If the new job is from a higher confidence source, swap it to primary
                if new_conf > existing_conf:
                    # Move existing primary to alternative
                    existing.setdefault('alternative_apply_sources', []).append({
                        'platform': existing.get('source_platform'),
                        'url': existing.get('apply_url'),
                        'confidence': existing_conf
                    })
                    
                    # Update existing with new primary details
                    existing['apply_url'] = job.get('apply_url')
                    existing['source_platform'] = job.get('source_platform')
                    existing['source_connector'] = job.get('source_connector')
                    existing['confidence'] = new_conf
                    existing['raw_payload'] = job.get('raw_payload')
                else:
                    # Append new job to alternative sources
                    existing.setdefault('alternative_apply_sources', []).append({
                        'platform': job.get('source_platform'),
                        'url': job.get('apply_url'),
                        'confidence': new_conf
                    })

        return list(unique_jobs.values())
