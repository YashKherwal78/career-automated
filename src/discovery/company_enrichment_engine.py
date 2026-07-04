import logging
import sqlite3
from typing import Dict, Any
from src.discovery.event_bus import event_bus
from src.crm.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompanyEnrichmentEngine:
    """
    Listens for newly discovered companies, enriches their metadata, and transitions 
    their lifecycle state from DISCOVERED to ENRICHING to VERIFIED.
    Emits a CompanyEnrichedEvent upon success.
    """
    def __init__(self):
        event_bus.subscribe('CompanyCreatedEvent', self.handle_company_created)
        
    def handle_company_created(self, payload: Dict[str, Any]):
        """
        Handler for CompanyCreatedEvent.
        Payload expects: company_name, source, discovery_type, website, careers_url
        """
        company_name = payload.get('company_name')
        if not company_name:
            logger.error("CompanyCreatedEvent missing company_name")
            return
            
        logger.info(f"EnrichmentEngine processing {company_name}")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Insert into company_intelligence_static as DISCOVERED
        website = payload.get('website', '')
        careers_url = payload.get('careers_url', '')
        
        try:
            cursor.execute('''
                INSERT INTO company_intelligence_static (company_name, website, careers_url, lifecycle_status, discovery_source)
                VALUES (?, ?, ?, 'ENRICHING', ?)
            ''', (company_name, website, careers_url, payload.get('source', '')))
        except sqlite3.IntegrityError:
            # Already exists, just update state if it's new
            cursor.execute('''
                UPDATE company_intelligence_static 
                SET lifecycle_status = 'ENRICHING', updated_at = CURRENT_TIMESTAMP
                WHERE company_name = ? AND lifecycle_status IN ('NEW', 'DISCOVERED')
            ''', (company_name,))
        
        # Insert attribution
        cursor.execute('''
            INSERT INTO company_discovery_sources (company_name, source, discovery_type)
            VALUES (?, ?, ?)
            ON CONFLICT(company_name, source, discovery_type) DO UPDATE SET 
            last_seen = CURRENT_TIMESTAMP, confidence = confidence + 1
        ''', (company_name, payload.get('source', 'Unknown'), payload.get('discovery_type', 'Company Discovery')))
        
        conn.commit()
        
        # 2. Perform Enrichment (e.g., search for official website if missing, find investors)
        # Mocking enrichment logic for now
        enriched_website = website if website else f"https://www.{company_name.lower().replace(' ', '')}.com"
        
        # 3. Transition to VERIFIED
        cursor.execute('''
            UPDATE company_intelligence_static 
            SET website = ?, lifecycle_status = 'VERIFIED', updated_at = CURRENT_TIMESTAMP
            WHERE company_name = ?
        ''', (enriched_website, company_name))
        conn.commit()
        conn.close()
        
        logger.info(f"Company {company_name} enriched and verified.")
        
        # 4. Emit CompanyEnrichedEvent
        event_bus.publish('CompanyEnrichedEvent', {
            'company_name': company_name,
            'website': enriched_website,
            'careers_url': careers_url
        })
        
if __name__ == "__main__":
    engine = CompanyEnrichmentEngine()
    # Mock loop to process events
    # event_bus.process_pending_events()
