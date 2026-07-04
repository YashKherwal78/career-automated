import logging
from src.discovery.importers.source_manager import SourceManager
from src.discovery.role_discovery_engine import RoleDiscoveryEngine
from src.discovery.event_bus import event_bus
from src.crm.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompanyDiscoveryEngine:
    """
    Central orchestrator for discovering startups.
    Coordinates VC Portfolios, YC Directory, Curated Repos, Product Hunt, 
    and the Role Discovery Inbox.
    Outputs exclusively to the Event Bus (CompanyCreatedEvent).
    """
    
    def __init__(self):
        self.source_manager = SourceManager()
        self.role_discovery = RoleDiscoveryEngine()
        
    def _get_existing_companies(self) -> set:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT company_name FROM company_registry")
        existing = {row[0].lower() for row in cursor.fetchall()}
        conn.close()
        return existing
        
    def run_discovery(self):
        """
        Executes all company discovery streams.
        """
        logger.info("Starting Company Discovery Engine Orchestration...")
        
        existing_companies = self._get_existing_companies()
        
        # 1. Run Data Source Importers (VCs, Repos, CSVs)
        logger.info("Polling Curated Data Sources...")
        datasets = self.source_manager.run_all_sources()
        
        # In a real implementation, datasets would be parsed into standardized company dicts
        for company_data in datasets:
            company_name = company_data.get('company_name')
            if not company_name:
                continue
                
            company_lower = company_name.lower()
            if company_lower not in existing_companies:
                logger.info(f"Company Discovery found NEW company via datasets: {company_name}")
                event_bus.publish('CompanyCreatedEvent', {
                    'company_name': company_name,
                    'source': company_data.get('source_name', 'Unknown Source'),
                    'discovery_type': company_data.get('discovery_type', 'Company Discovery'),
                    'website': company_data.get('website', ''),
                    'careers_url': company_data.get('careers_url', '')
                })
                existing_companies.add(company_lower)
            else:
                event_bus.publish('CompanySeenEvent', {
                    'company_name': company_name,
                    'source': company_data.get('source_name', 'Unknown Source'),
                    'discovery_type': company_data.get('discovery_type', 'Company Discovery')
                })
                
        # 2. Run Role Discovery Inbox (The 5% targeted search)
        logger.info("Executing Role Discovery Inbox...")
        self.role_discovery.run_discovery_inbox()
        
        logger.info("Company Discovery Engine Orchestration Complete.")

if __name__ == "__main__":
    engine = CompanyDiscoveryEngine()
    engine.run_discovery()
