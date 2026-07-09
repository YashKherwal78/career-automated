import aiohttp
from urllib.parse import urlparse
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class RecruiteeInspector(SourceInspector):
    @property
    def source_name(self) -> str:
        return "recruitee"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname != 'recruitee.com' and hostname.endswith('.recruitee.com'):
            slug = hostname.split('.')[0]
        else:
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            slug = path_parts[0] if path_parts else ""
            
        if not slug:
            return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
            
        # Recruitee has a public API: https://api.recruitee.com/c/{slug}/careers/
        api_url = f"https://api.recruitee.com/c/{slug}/careers/"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return InspectionResult(
                            board_exists=True,
                            job_count=1,
                            api_verified=True,
                            canonical_company=slug.capitalize(),
                            endpoint=api_url,
                            identity=StandardBoardIdentity(ats='recruitee', board_token=slug)
                        )
            except Exception:
                pass
        return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
