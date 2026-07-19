import re
from typing import AsyncIterator
from bs4 import BeautifulSoup
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

import logging
logger = logging.getLogger("BambooHRConnector")

class BambooHRConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_bulk_fetch=False,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        from urllib.parse import urlparse
        parsed = urlparse(board.endpoint)
        slug = parsed.hostname.split('.bamboohr.com')[0] if parsed.hostname else 'unknown'
        api_url = f"https://{slug}.bamboohr.com/jobs/embed2.php"
            
        headers = {"User-Agent": "Mozilla/5.0"}
        etag = board.metadata.get("etag")
        
        result = await http_client.fetch("GET", api_url, headers=headers, etag=etag)
        
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result
        
        if not should_sync:
            logger.info(f"BambooHRConnector[{slug}] - Content unchanged. Skipping sync.")
            return
            
        if result.status_code == 200 and result.payload:
            html = result.payload
            soup = BeautifulSoup(html, "html.parser")
            
            department_blocks = soup.find_all("li", class_="BambooHR-ATS-Department-Item")
            
            for dept_block in department_blocks:
                header = dept_block.find("div", class_="BambooHR-ATS-Department-Header")
                dept_name = header.get_text(strip=True) if header else None
                
                jobs = dept_block.find_all("li", class_="BambooHR-ATS-Jobs-Item")
                for job_li in jobs:
                    link = job_li.find("a")
                    loc_span = job_li.find("span", class_="BambooHR-ATS-Location")
                    
                    if link:
                        title = link.get_text(strip=True)
                        href = link.get("href")
                        
                        url = href if href.startswith("http") else (
                            f"https:{href}" if href.startswith("//")
                            else f"https://{slug}.bamboohr.com{href}"
                        )
                        
                        loc = loc_span.get_text(strip=True) if loc_span else None
                        
                        # Match id
                        job_id_match = re.search(r'bhrPositionID_(\d+)', job_li.get("id", ""))
                        job_id = job_id_match.group(1) if job_id_match else None
                        
                        payload = {
                            "title": title,
                            "url": url,
                            "location": loc,
                            "department": dept_name,
                            "id": job_id
                        }
                        
                        yield RawJob(company_id=board.company_id, provider="bamboohr", board_identity=board.identity, payload=payload)

ConnectorRegistry.register('bamboohr', 'HTML', 10, BambooHRConnector)
