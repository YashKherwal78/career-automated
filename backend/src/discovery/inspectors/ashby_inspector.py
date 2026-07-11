import aiohttp
from typing import Dict, Any
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class AshbyInspector(SourceInspector):
    
    @property
    def source_name(self) -> str:
        return "ashby"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        board_token = url.rstrip('/').split('/')[-1]
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
            
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
                        job_board = data.get("jobBoard", {})
                        postings = data.get("jobs", job_board.get("jobPostings", []))
                        
                        return InspectionResult(
                            board_exists=True,
                            job_count=len(postings),
                            api_verified=True,
                            canonical_company=job_board.get("name", ""),
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
