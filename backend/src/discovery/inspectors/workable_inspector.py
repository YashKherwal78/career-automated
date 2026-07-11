import aiohttp
from urllib.parse import urlparse
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class WorkableInspector(SourceInspector):
    
    @property
    def source_name(self) -> str:
        return "workable"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        """
        Validates the Workable board by trying to hit their API.
        e.g., https://apply.workable.com/whatsapp -> 
        https://apply.workable.com/api/v3/accounts/whatsapp/jobs
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        slug = path.split('/')[0] if path else ""
        
        if not slug:
            return InspectionResult(
                board_exists=False,
                job_count=0,
                api_verified=False,
                canonical_company="",
                endpoint=url,
                identity=StandardBoardIdentity(ats='workable', board_token=slug)
            )
            
        api_url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
        payload = {"query": "", "location": [], "department": [], "worktype": [], "precision": "any"}
            
        async with aiohttp.ClientSession() as session:
            try:
                # Workable API expects a POST request to this endpoint
                async with session.post(api_url, json=payload, timeout=15) as response:
                    if response.status == 404:
                        return InspectionResult(
                            board_exists=False,
                            job_count=0,
                            api_verified=True,
                            canonical_company="",
                            endpoint=api_url,
                            identity=StandardBoardIdentity(ats='workable', board_token=slug)
                        )
                    elif response.status == 200:
                        data = await response.json()
                        # Output contains 'totalSize'
                        total = data.get("totalSize", 0)
                        return InspectionResult(
                            board_exists=True,
                            job_count=total,
                            api_verified=True,
                            canonical_company=slug.capitalize(),
                            endpoint=api_url,
                            identity=StandardBoardIdentity(ats='workable', board_token=slug)
                        )
                    else:
                        return InspectionResult(
                            board_exists=False,
                            job_count=0,
                            api_verified=False,
                            canonical_company="",
                            endpoint=api_url,
                            identity=StandardBoardIdentity(ats='workable', board_token=slug)
                        )
            except Exception:
                return InspectionResult(
                    board_exists=False,
                    job_count=0,
                    api_verified=False,
                    canonical_company="",
                    endpoint=api_url,
                    identity=StandardBoardIdentity(ats='workable', board_token=slug)
                )
