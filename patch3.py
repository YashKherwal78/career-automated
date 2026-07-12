import re

with open('src/discovery/workers/smartrecruiters_adapter.py', 'r') as f:
    content = f.read()

new_fetch = """        async with aiohttp.ClientSession() as session:
            try:
                while True:
                    paginated_url = f"{api_url}?limit={limit}&offset={offset}"
                    logger.info(f"[{company_id}] Fetching SR page: {paginated_url}")
                    
                    async with session.get(paginated_url, headers=headers, timeout=15) as response:
                        if response.status != 200:
                            logger.warning(f"[{company_id}] Failed SR fetch: {response.status} {response.url}")
                            break
                            
                        data = await response.json()
                        content = data.get("content", [])
                        if not content:
                            break
                            
                        all_jobs.extend(content)
                        
                        if len(content) < limit:
                            break # Reached the last page
                            
                        offset += limit
            except Exception as e:
                logger.error(f"[{company_id}] Network failure during fetch: {e}")"""

start_fetch = content.find("        async with aiohttp.ClientSession() as session:")
end_fetch = content.find("        return {\"company_id\": company_id, \"source_url\": url, \"jobPostings\": all_jobs}")

if start_fetch != -1 and end_fetch != -1:
    content = content[:start_fetch] + new_fetch + "\n\n" + content[end_fetch:]

new_jobs = """        for p in postings:
            title = p.get("name")
            location_obj = p.get("location", {})
            city = location_obj.get("city", "")
            region = location_obj.get("region", "")
            country = location_obj.get("country", "")
            location = f"{city}, {region}, {country}".strip(", ")
            job_url = p.get("ref", "")
            
            if title and job_url:
                jobs.append({
                    "title": title,
                    "location": location,
                    "employment_type": p.get("typeOfEmployment", {}).get("label", "full-time").lower() if p.get("typeOfEmployment") else "full-time",
                    "url": job_url,
                    "provider_job_id": p.get("id", ""),
                    "updated_at": p.get("releasedDate", ""),
                    "provider": "smartrecruiters"
                })"""

start_jobs = content.find("        for p in postings:")
end_jobs = content.find("        return jobs")

if start_jobs != -1 and end_jobs != -1:
    content = content[:start_jobs] + new_jobs + "\n" + content[end_jobs:]

with open('src/discovery/workers/smartrecruiters_adapter.py', 'w') as f:
    f.write(content)
print("Patched successfully")
