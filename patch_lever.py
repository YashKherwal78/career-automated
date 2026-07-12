import re

with open('src/discovery/workers/lever_adapter.py', 'r') as f:
    content = f.read()

# 1. Network Resilience Patch
new_fetch = """        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=15) as response:
                    if response.status != 200:
                        return {"jobs": []}
                    data = await response.json()
                    if isinstance(data, list):
                        return {"jobs": data}
                    return data
            except Exception as e:
                return {"jobs": []}"""

content = re.sub(r'        async with aiohttp\.ClientSession\(\) as session:.*return data', new_fetch, content, flags=re.DOTALL)

# 2. Schema Patch
new_jobs = """        jobs = []
        for raw_job in parsed_data.get("jobs", []):
            categories = raw_job.get("categories", {})
            job = {
                "title": raw_job.get("text"),
                "location": categories.get("location", "unknown"),
                "employment_type": categories.get("commitment", "full-time").lower(),
                "url": raw_job.get("hostedUrl"),
                "provider_job_id": str(raw_job.get("id")),
                "updated_at": str(raw_job.get("createdAt")),
                "provider": "lever"
            }
            jobs.append(job)
        return jobs"""

content = re.sub(r'        jobs = \[\]\n        for raw_job in parsed_data\.get\("jobs", \[\]\):.*return jobs', new_jobs, content, flags=re.DOTALL)

with open('src/discovery/workers/lever_adapter.py', 'w') as f:
    f.write(content)
