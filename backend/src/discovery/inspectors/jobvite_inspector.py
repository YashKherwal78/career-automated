import aiohttp
from urllib.parse import urlparse
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class JobviteInspector(SourceInspector):
    @property
    def source_name(self) -> str:
        return "jobvite"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        slug = path_parts[0] if path_parts else ""
        if slug == 'careers' and len(path_parts) > 1:
            slug = path_parts[1]
            
        if not slug:
            return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
            
        # Jobvite XML feed: https://www.jobvite.com/CompanyJobs/XmlFeed.aspx?c={slug}
        api_url = f"https://www.jobvite.com/CompanyJobs/XmlFeed.aspx?c={slug}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=10) as response:
                    if response.status == 200:
                        return InspectionResult(
                            board_exists=True,
                            job_count=1,
                            api_verified=True,
                            canonical_company=slug.capitalize(),
                            endpoint=api_url,
                            identity=StandardBoardIdentity(ats='jobvite', board_token=slug)
                        )
            except Exception:
                pass
        return InspectionResult(board_exists=False, job_count=0, api_verified=False, canonical_company="", endpoint=url)
