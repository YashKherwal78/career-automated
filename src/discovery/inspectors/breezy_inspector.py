import aiohttp
from urllib.parse import urlparse
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class BreezyInspector(SourceInspector):
    @property
    def source_name(self) -> str:
        return "breezy"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname != 'breezy.hr' and hostname.endswith('.breezy.hr'):
            slug = hostname.split('.')[0]
        else:
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            slug = path_parts[0] if path_parts else ""
            
        if not slug:
            return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
            
        # Breezy has a public API: https://api.breezy.hr/v1/public/positions?company_id={slug}
        # Or we can inspect the careers URL: https://{slug}.breezy.hr/
        test_url = f"https://{slug}.breezy.hr/"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(test_url, timeout=10) as response:
                    if response.status == 200:
                        return InspectionResult(
                            board_exists=True,
                            job_count=1,
                            api_verified=True,
                            canonical_company=slug.capitalize(),
                            endpoint=test_url,
                            identity=StandardBoardIdentity(ats='breezy', board_token=slug)
                        )
            except Exception:
                pass
        return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
