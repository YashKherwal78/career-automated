import asyncio
import logging
from src.discovery.workers.workday_adapter import WorkdayAdapter

logging.basicConfig(level=logging.INFO)

async def test_regression():
    tenants = [
        ("Nvidia", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"),
        ("PVH", "https://pvh.wd1.myworkdayjobs.com/PVH_Careers"),
        ("Roblox", "https://roblox.wd1.myworkdayjobs.com/roblox"),
        ("Netflix", "https://netflix.wd1.myworkdayjobs.com/Netflix_Careers"),
        ("Visa", "https://visa.wd1.myworkdayjobs.com/visa")
    ]
    
    adapter = WorkdayAdapter()
    
    success = 0
    failed = 0
    
    for name, url in tenants:
        try:
            print(f"\n--- Testing {name} ---")
            task = {"company_id": name, "url": url}
            raw = await adapter.fetch(task)
            parsed = adapter.parse(raw)
            jobs = adapter.discover_jobs(parsed)
            print(f"Success! Found {len(jobs)} jobs for {name}")
            success += 1
        except Exception as e:
            print(f"Failed {name}: {e}")
            failed += 1
            
    print(f"\nResults: {success}/{len(tenants)} ({success/len(tenants)*100:.1f}%)")

if __name__ == '__main__':
    asyncio.run(test_regression())
