import re

with open('src/discovery/run_cluster.py', 'r') as f:
    content = f.read()

# Replace the seeding logic
new_logic = """
                    WHEN career_url LIKE '%ashbyhq.com%' THEN 'ashby'
                    WHEN career_url LIKE '%myworkdayjobs.com%' THEN 'workday'
                    WHEN career_url LIKE '%smartrecruiters.com%' THEN 'smartrecruiters'
                    ELSE ats_provider
                END as detected_provider
            FROM career_endpoints 
            WHERE career_url LIKE '%greenhouse.io%' 
               OR ats_provider = 'greenhouse'
               OR career_url LIKE '%lever.co%'
               OR ats_provider = 'lever'
               OR career_url LIKE '%ashbyhq.com%'
               OR ats_provider = 'ashby'
               OR career_url LIKE '%myworkdayjobs.com%'
               OR ats_provider = 'workday'
               OR career_url LIKE '%smartrecruiters.com%'
               OR ats_provider = 'smartrecruiters'
"""

start_idx = content.find("                    WHEN career_url LIKE '%ashbyhq.com%' THEN 'ashby'")
end_idx = content.find("        endpoints = cursor.fetchall()")

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_logic + "        " + content[end_idx:]
    with open('src/discovery/run_cluster.py', 'w') as f:
        f.write(new_content)
    print("Patched successfully")
else:
    print("Could not find the block to replace")
