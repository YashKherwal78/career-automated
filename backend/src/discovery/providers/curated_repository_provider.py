from src.system.logger import setup_logger
logger = setup_logger('curated_repository_provider')
from typing import List, Optional
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.discovery.importers.source_manager import SourceManager
from src.discovery.parsers.markdown_job_parser import MarkdownJobParser
from src.crm.database import get_connection, add_discovery_source
from src.discovery.ats_detector import ATSDetector
from src.discovery.company_intelligence_engine import CompanyIntelligenceEngine

class CuratedRepositoryProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.source_manager = SourceManager()
        self.markdown_parser = MarkdownJobParser()
        self.ats_detector = ATSDetector()
        self.intelligence_engine = CompanyIntelligenceEngine()

    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            requires_api_key=False,
            rate_limit_per_minute=0, # Local execution
            supports_pagination=False,
            supports_incremental_sync=True,
            supports_remote_jobs=True,
            supports_search_filters=False
        )

    def validate_configuration(self) -> bool:
        return True

    def _check_company_exists(self, company_name: str) -> bool:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT 1 FROM company_intelligence_static WHERE company_name = ?", (company_name,))
        exists = c.fetchone() is not None
        conn.close()
        return exists

    def _register_new_company(self, company_name: str, url: str = None, source_name: str = "Curated Repository"):
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO company_intelligence_static 
            (company_name, careers_url, lifecycle_status, discovery_source)
            VALUES (?, ?, 'NEW', ?)
        ''', (company_name, url, source_name))
        conn.commit()
        conn.close()

        # Try ATS Detection on the direct apply URL
        if url:
            detection = self.ats_detector.detect_ats(url)
            if detection["ats_provider"] != "unknown":
                conn = get_connection()
                c = conn.cursor()
                ats = detection["ats_provider"]
                slug = detection["slug"]
                gh_slug = slug if ats == "greenhouse" else None
                lever_slug = slug if ats == "lever" else None
                ashby_slug = slug if ats == "ashby" else None
                
                c.execute('''
                    UPDATE company_intelligence_static
                    SET ats_provider = ?, greenhouse_slug = ?, lever_slug = ?, ashby_slug = ?, lifecycle_status = 'ATS_FOUND'
                    WHERE company_name = ?
                ''', (ats, gh_slug, lever_slug, ashby_slug, company_name))
                conn.commit()
                conn.close()

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str], target_companies: Optional[List[dict]] = None) -> List[StandardJob]:
        all_jobs = []
        
        # 1. Sync all sources
        sync_results = self.source_manager.sync_all_sources()
        
        # 2. Parse incrementally added files
        for result in sync_results:
            source = result["source"]
            parser_type = source.get("parser")
            
            for file_path in result["files"]:
                if parser_type == "markdown_table":
                    parsed_jobs = self.markdown_parser.parse_file(file_path, source["name"])
                    
                    for job in parsed_jobs:
                        # Deduplicate & Enrich
                        if not self._check_company_exists(job.company):
                            self._register_new_company(job.company, job.application_url, source["name"])
                        add_discovery_source(job.company, source["name"])
                        
                    all_jobs.extend(parsed_jobs)
                else:
                    logger.info(f"Parser {parser_type} not yet implemented.")
                    
        # 3. Recompute intelligence for priority scheduler
        if all_jobs:
            self.intelligence_engine.compute_all()
            
        return all_jobs
