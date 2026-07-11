import aiohttp
from urllib.parse import urlparse
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.models import InspectionResult, WorkdayBoardIdentity

class WorkdayInspector(SourceInspector):
    
    @property
    def source_name(self) -> str:
        return "workday"
        
    async def inspect_board(self, url: str) -> InspectionResult:
        """
        Validates the Workday board by trying to hit the CXS jobs API.
        e.g., https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite -> 
        https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs
        """
        parsed = urlparse(url)
        hostname = parsed.hostname
        path = parsed.path.strip('/')
        
        # E.g., nvidia.wd5.myworkdayjobs.com -> tenant="nvidia", instance="wd5"
        parts = hostname.split('.')
        tenant = parts[0]
        site = parts[1] if len(parts) > 1 else 'External_Career_Site'
        
        # Site name is usually the first path part, e.g., NVIDIAExternalCareerSite
        site_name = path.split('/')[0] if path else ""
        
        if not site_name:
            return InspectionResult(
                board_exists=False,
                job_count=0,
                api_verified=False,
                canonical_company="",
                endpoint=url,
            identity=WorkdayBoardIdentity(ats='workday', tenant=tenant, site=site_name)
            )
            
        api_url = f"https://{hostname}/wday/cxs/{tenant}/{site_name}/jobs"
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(api_url, json=payload, timeout=15) as response:
                    if response.status == 404:
                        return InspectionResult(
                            board_exists=False,
                            job_count=0,
                            api_verified=True,
                            canonical_company="",
                            endpoint=api_url,
                            identity=WorkdayBoardIdentity(ats='workday', tenant=tenant, site=site_name)
                        )
                    elif response.status == 200:
                        data = await response.json()
                        total = data.get("total", 0)
                        
                        return InspectionResult(
                            board_exists=True,
                            job_count=total,
                            api_verified=True,
                            canonical_company=tenant, # Workday rarely gives the clean company name here, use tenant
                            endpoint=api_url,
                            identity=WorkdayBoardIdentity(ats='workday', tenant=tenant, site=site_name)
                        )
                    else:
                        return InspectionResult(
                            board_exists=False,
                            job_count=0,
                            api_verified=False,
                            canonical_company="",
                            endpoint=api_url,
                            identity=WorkdayBoardIdentity(ats='workday', tenant=tenant, site=site_name)
                        )
            except Exception as e:
                return InspectionResult(
                    board_exists=False,
                    job_count=0,
                    api_verified=False,
                    canonical_company="",
                    endpoint=api_url,
                            identity=WorkdayBoardIdentity(ats='workday', tenant=tenant, site=site_name)
                        )
