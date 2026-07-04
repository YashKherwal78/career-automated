import logging
from typing import List, Dict, Any
from src.discovery.event_bus import event_bus
from src.discovery.providers.provider_manager import ProviderManager
from src.discovery.query_generator import QueryGenerator
from src.crm.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoleDiscoveryEngine:
    """
    A lightweight engine dedicated to querying high-value roles across backends.
    Its sole purpose is to parse jobs, extract the Company, and inject new companies 
    into the Registry via the Event Bus. It never applies to these jobs.
    """
    
    def __init__(self):
        self.provider_manager = ProviderManager()
        self.query_generator = QueryGenerator()
        
    def _get_existing_companies(self) -> set:
        """Cache existing companies to avoid unnecessary event emission."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT company_name FROM company_registry")
        existing = {row[0].lower() for row in cursor.fetchall()}
        conn.close()
        return existing
        
    def run_discovery_inbox(self):
        """
        Executes the Discovery Inbox logic: searching the open internet for roles to discover startups.
        """
        logger.info("Starting Role Discovery Inbox...")
        
        existing_companies = self._get_existing_companies()
        
        # We only generate generic queries for this engine.
        queries = [
            "Associate Product Manager India startup",
            "Product Manager startup",
            "AI Engineer startup",
            "Applied AI Engineer",
            "Founder's Office startup",
            "Machine Learning Engineer India"
        ]
        
        # Use generic search provider, e.g., Indeed or generic internet search provider
        # For demonstration we assume IndeedProvider is accessed via the ProviderManager
        # In a real run, we might use InternetSearchProvider or Apify.
        
        discovered_count = 0
        
        for query in queries:
            logger.info(f"Role Discovery searching for: {query}")
            # Mocking the call to the provider manager to just get jobs
            # e.g., jobs = self.provider_manager.search("internet", query=query, location="India")
            # For this architecture, we emit events for each unique company found.
            
            # Since ProviderManager returns standardized jobs:
            try:
                # Assuming internet search is set as a fallback or default
                jobs = self.provider_manager.execute_providers(query, "Remote India", 
                                                             limit_per_provider=10)
            except Exception as e:
                logger.error(f"Error executing providers for query {query}: {e}")
                continue
                
            for job in jobs:
                company = job.get("company")
                if not company:
                    continue
                    
                company_lower = company.lower()
                
                # If company is not in the registry, we've found a new startup!
                if company_lower not in existing_companies:
                    logger.info(f"Role Discovery Inbox found NEW company: {company}")
                    
                    # Emit Company Created Event
                    event_bus.publish('CompanyCreatedEvent', {
                        'company_name': company,
                        'source': job.get('source', 'Internet Search'),
                        'discovery_type': 'Role Discovery',
                        'website': job.get('company_url', ''),
                        'careers_url': job.get('url', ''),
                        'ats_provider': job.get('ats', '')
                    })
                    
                    existing_companies.add(company_lower)
                    discovered_count += 1
                else:
                    # Publish a Company Seen Event to update attribution
                    event_bus.publish('CompanySeenEvent', {
                        'company_name': company,
                        'source': job.get('source', 'Internet Search'),
                        'discovery_type': 'Role Discovery'
                    })
                    
        logger.info(f"Role Discovery Inbox complete. Discovered {discovered_count} new companies.")
        
if __name__ == "__main__":
    engine = RoleDiscoveryEngine()
    engine.run_discovery_inbox()
