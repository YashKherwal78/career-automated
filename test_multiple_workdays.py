import asyncio
from src.discovery.models import WorkdayBoardIdentity, RawJob
import src.discovery.workers.workday_adapter
from src.discovery.registry.source_registry import SourceRegistry
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.pipeline.job_validator import JobValidator
from src.discovery.inspectors.workday_inspector import WorkdayInspector

async def test_workday_company(company_name, url):
    print(f"\n--- Testing WORKDAY ({company_name}) ---")
    
    # 1. Inspection (Identity Extraction)
    inspector = WorkdayInspector()
    result = await inspector.inspect_board(url)
    if not result.board_exists or not isinstance(result.identity, WorkdayBoardIdentity):
        print("❌ Inspection Failed: Could not verify or extract identity.")
        return False
        
    identity = result.identity
    print(f"✅ Extracted Identity: tenant='{identity.tenant}', site='{identity.site}'")
    
    # 2. Fetch (just first page to save time)
    adapter = SourceRegistry.get_adapter("workday")
    
    # Workday adapter dynamically paginates if we call fetch. Let's patch limit to 1 page for this test.
    # Actually, we can just call the endpoint directly for the first page
    import aiohttp
    api_url = f"https://{identity.tenant}.wd1.myworkdayjobs.com/wday/cxs/{identity.tenant}/{identity.site}/jobs"
    if "wd5" in url:
        api_url = api_url.replace("wd1", "wd5")
        
    payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=payload) as response:
            if response.status != 200:
                print(f"❌ Failed to fetch jobs API: {response.status}")
                return False
            raw_data = await response.json()
            
    # 3. RawJob -> Normalizer
    raw_job = adapter.discover_jobs(raw_data, board_identity=identity)
    normalizer = NormalizerFactory.get_normalizer("workday")
    canonical_jobs = normalizer.normalize(raw_job)
    
    print(f"✅ Normalizer output: {len(canonical_jobs)} CanonicalJobs")
    if not canonical_jobs:
        print("❌ FAILED: 0 jobs extracted.")
        return False
        
    valid, invalid = JobValidator.filter_valid(canonical_jobs)
    print(f"✅ Validation: {len(valid)} valid, {len(invalid)} invalid")
    
    if valid:
        first_job = valid[0]
        print(f"✅ Example CanonicalJob:")
        print(f"  Title:   {first_job.title}")
        print(f"  Company: {first_job.company_id}")
        print(f"  Loc:     {first_job.location}")
        print(f"  URL:     {first_job.apply_url}")
        print(f"  Ident:   {first_job.identity.get_hash()}")
    
    return True

async def main():
    companies = [
        ("Nvidia", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"),
        ("Salesforce", "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site"),
        ("Target", "https://target.wd5.myworkdayjobs.com/TargetCareers"),
        ("FedEx", "https://fedex.wd1.myworkdayjobs.com/FedEx_Careers"),
    ]
    for name, url in companies:
        await test_workday_company(name, url)

if __name__ == "__main__":
    asyncio.run(main())
