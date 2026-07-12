import asyncio

import src.discovery.workers.smartrecruiters_adapter
import src.discovery.workers.greenhouse_adapter
import src.discovery.workers.ashby_adapter
import src.discovery.workers.lever_adapter
import src.discovery.workers.workday_adapter

from src.discovery.models import StandardBoardIdentity, WorkdayBoardIdentity
from src.discovery.registry.source_registry import SourceRegistry
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.pipeline.job_validator import JobValidator

async def test_provider(company_name, ats, board_id, url, tenant=None, site=None):
    print(f"\n--- Testing {ats.upper()} ({company_name}) ---")
    
    adapter = SourceRegistry.get_adapter(ats)
    try:
        raw_data = await adapter.fetch({"url": url, "company_id": company_name})
        
        if ats == "workday":
            identity = WorkdayBoardIdentity(ats=ats, tenant=tenant, site=site)
        else:
            identity = StandardBoardIdentity(ats=ats, board_token=board_id)
            
        raw_job = adapter.discover_jobs(raw_data, board_identity=identity)
        print(f"✅ RawJob created with payload keys: {list(raw_job.payload.keys())[:5]}")
        
        normalizer = NormalizerFactory.get_normalizer(ats)
        canonical_jobs = normalizer.normalize(raw_job)
        print(f"✅ Normalizer output: {len(canonical_jobs)} CanonicalJobs")
        
        if not canonical_jobs:
            print("❌ FAILED: 0 jobs extracted.")
            return False
            
        valid, invalid = JobValidator.filter_valid(canonical_jobs)
        print(f"✅ Validation: {len(valid)} valid, {len(invalid)} invalid")
        
        if invalid:
            print(f"❌ FIRST INVALID JOB ERRORS: {invalid[0]['errors']}")
            return False
            
        first_job = valid[0]
        print(f"✅ Example CanonicalJob:")
        print(f"  Title:   {first_job.title}")
        print(f"  Company: {first_job.company_id}")
        print(f"  Loc:     {first_job.location}")
        print(f"  URL:     {first_job.apply_url}")
        print(f"  Ident:   {first_job.identity.get_hash()}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED with Exception: {e}")
        return False

async def main():
    success = True
    # Test all 5
    success &= await test_provider("Visa", "smartrecruiters", "Visa", "https://jobs.smartrecruiters.com/Visa") # Will be 0 jobs but that's ok
    success &= await test_provider("Figma", "greenhouse", "figma", "https://boards.greenhouse.io/figma")
    success &= await test_provider("Notion", "ashby", "notion", "https://api.ashbyhq.com/posting-api/job-board/notion")
    success &= await test_provider("Spotify", "lever", "spotify", "https://api.lever.co/v0/postings/spotify")
    success &= await test_provider("Nvidia", "workday", "NVIDIAExternalCareerSite", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", tenant="nvidia", site="NVIDIAExternalCareerSite")
    
    if success:
        print("\n🎉 ALL PROVIDERS PASSED PHASE 1 END-TO-END VALIDATION!")

if __name__ == "__main__":
    asyncio.run(main())
