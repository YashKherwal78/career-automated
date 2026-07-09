import aiohttp
from urllib.parse import urlparse
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class TeamtailorInspector(SourceInspector):
    @property
    def source_name(self) -> str:
        return "teamtailor"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname != 'teamtailor.com' and hostname.endswith('.teamtailor.com'):
            slug = hostname.split('.')[0]
        else:
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            slug = path_parts[0] if path_parts else ""
            
        if not slug:
            return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
            
        test_url = f"https://{slug}.teamtailor.com/"
        async with aiohttp.ClientSession() as session:
            try:
                # We do a GET and check page title or response status
                async with session.get(test_url, timeout=10) as response:
                    if response.status == 200:
                        return InspectionResult(
                            board_exists=True,
                            job_count=1,  # Indicate active status
                            api_verified=True,
                            canonical_company=slug.capitalize(),
                            endpoint=test_url,
                            identity=StandardBoardIdentity(ats='teamtailor', board_token=slug)
                        )
            except Exception:
                pass
        return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
