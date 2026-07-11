import aiohttp
from typing import Dict, Any
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, StandardBoardIdentity

class GreenhouseInspector(SourceInspector):
    
    @property
    def source_name(self) -> str:
        return "greenhouse"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        board_token = url.rstrip('/').split('/')[-1]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}"
            
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
                        jobs = data.get("jobs", [])
                        
                        return InspectionResult(
                            board_exists=True,
                            job_count=len(jobs),
                            api_verified=True,
                            canonical_company=data.get("name", ""),
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
