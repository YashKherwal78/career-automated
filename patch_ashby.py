import re

with open('src/discovery/workers/ashby_adapter.py', 'r') as f:
    content = f.read()

# 1. Network Resilience Patch
new_fetch = """        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=15) as response:
                    if response.status != 200:
                        return {"jobBoard": {"jobPostings": []}}
                    return await response.json()
            except Exception as e:
                return {"jobBoard": {"jobPostings": []}}"""

content = re.sub(r'        async with aiohttp\.ClientSession\(\) as session:.*return await response\.json\(\)', new_fetch, content, flags=re.DOTALL)

# 2. Schema Patch
new_jobs = """        jobs = []
        job_board = parsed_data.get("jobBoard", {})
        postings = parsed_data.get("jobs", job_board.get("jobPostings", []))
        
        for raw_job in postings:
            location = raw_job.get("locationName", "")
            if not location and "location" in raw_job:
                location = raw_job["location"]
                
            job = {
                "title": raw_job.get("title"),
                "location": location,
                "employment_type": raw_job.get("employmentType", "full-time").lower(),
                "url": raw_job.get("jobUrl", raw_job.get("applyUrl")),
                "provider_job_id": str(raw_job.get("id")),
                "updated_at": raw_job.get("updatedAt", ""),
                "provider": "ashby"
            }
            jobs.append(job)
        return jobs"""

content = re.sub(r'        jobs = \[\]\n.*return jobs', new_jobs, content, flags=re.DOTALL)

with open('src/discovery/workers/ashby_adapter.py', 'w') as f:
    f.write(content)
