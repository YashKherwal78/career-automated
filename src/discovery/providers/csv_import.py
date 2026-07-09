import csv
import logging
from typing import List, Dict, Any, Optional
from src.discovery.providers.base_provider import BaseProvider
from src.discovery.providers.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)

class CSVImportProvider(BaseProvider):
    
    @property
    def provider_name(self) -> str:
        return "csv_import"
        
    @property
    def strategy_name(self) -> str:
        return "csv_import"

    async def discover(self, company_name: str, website_url: Optional[str] = None) -> List[Any]:
        # Filter the imported CSV for the company name
        companies = await self.discover_companies()
        results = []
        for c in companies:
            if c["company_name"].lower() == company_name.lower():
                from src.discovery.models import Candidate
                results.append(Candidate(
                    url=c["careers_url"],
                    source="csv_import",
                    source_page="data/companies_import.csv",
                    depth=0
                ))
        return results
        
    async def discover_companies(self) -> List[Dict[str, Any]]:
        """
        Reads candidate companies from a local CSV file.
        Format expected: Company Name, Career URL, ATS Provider
        """
        results = []
        try:
            with open('data/companies_import.csv', 'r') as f:
                reader = csv.reader(f)
                header = next(reader, None) # skip header
                for row in reader:
                    if len(row) >= 3:
                        results.append({
                            "company_name": row[0].strip(),
                            "careers_url": row[1].strip(),
                            "ats_provider": row[2].strip()
                        })
            logger.info(f"[CSVImportProvider] Read {len(results)} rows from data/companies_import.csv")
        except Exception as e:
            logger.error(f"[CSVImportProvider] Failed to read CSV: {e}")
            
        return results

ProviderRegistry.register(CSVImportProvider)
