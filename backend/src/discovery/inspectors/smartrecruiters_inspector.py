import aiohttp
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class SmartRecruitersInspector(SourceInspector):
    
    @property
    def source_name(self) -> str:
        return "smartrecruiters"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        """
        Extracts the SmartRecruiters board slug and hits their API.
        e.g., https://jobs.smartrecruiters.com/Visa -> https://api.smartrecruiters.com/v1/companies/Visa/postings
        """
        board_token = url.rstrip('/').split('/')[-1]
        api_url = f"https://api.smartrecruiters.com/v1/companies/{board_token}/postings"
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=15) as response:
                    if response.status == 404:
                        return InspectionResult(
                            board_exists=False,
                            job_count=0,
                            api_verified=True,
                            canonical_company="",
                            endpoint=api_url
                        )
                    elif response.status == 200:
                        data = await response.json()
                        jobs = data.get("content", [])
                        
                        # SR API has totalFound
                        total_jobs = data.get("totalFound", len(jobs))
                        
                        # Try to get company name from first job
                        canonical_company = board_token
                        if len(jobs) > 0 and "company" in jobs[0]:
                            canonical_company = jobs[0]["company"].get("name", board_token)
                        
                        return InspectionResult(
                            board_exists=True,
                            job_count=total_jobs,
                            api_verified=True,
                            canonical_company=canonical_company,
                            endpoint=api_url
                        )
                    else:
                        return InspectionResult(
                            board_exists=False,
                            job_count=0,
                            api_verified=False,
                            canonical_company="",
                            endpoint=api_url
                        )
            except Exception as e:
                return InspectionResult(
                    board_exists=False,
                    job_count=0,
                    api_verified=False,
                    canonical_company="",
                    endpoint=api_url
                )
