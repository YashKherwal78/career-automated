import aiohttp
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class LeverInspector(SourceInspector):
    
    @property
    def source_name(self) -> str:
        return "lever"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        """
        Extracts the Lever board slug and hits their API.
        e.g., https://jobs.lever.co/netflix -> https://api.lever.co/v0/postings/netflix?mode=json
        """
        board_token = url.rstrip('/').split('/')[-1]
        api_url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
            
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
                        # Lever API returns a list of jobs directly
                        jobs = data if isinstance(data, list) else []
                        
                        # Lever doesn't reliably return the company name in the job list itself,
                        # but we'll try to extract the company from the first job's hostedUrl if present
                        canonical_company = board_token 
                        
                        return InspectionResult(
                            board_exists=True,
                            job_count=len(jobs),
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
