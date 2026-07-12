import re

with open('src/discovery/company_discovery_engine.py', 'r') as f:
    content = f.read()

# Replace the validation block inside the concurrent function
new_logic = """
            if self.db.is_queued(url):
                metrics["skipped_duplicate"] += 1
                return
                
            # Generic Engine Validation (Provider Agnostic HTTP Ping)
            is_valid = False
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with semaphore:
                    async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                        # 406 is often returned by WAFs (like Workday) to bots, but implies the domain exists
                        if response.status in [200, 406]:
                            is_valid = True
            except Exception:
                pass
                
            if not is_valid:
                metrics["failed_validation"] += 1
                return
                
            self.db.insert_queue(name, url, provider_ats)
            metrics["queued"] += 1
"""

start_idx = content.find("            if self.db.is_queued(url):")
end_idx = content.find("            logger.info(f\"Queued new company: {name} ({url})\")") + len("            logger.info(f\"Queued new company: {name} ({url})\")")

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_logic + "\n" + content[end_idx:]
    with open('src/discovery/company_discovery_engine.py', 'w') as f:
        f.write(new_content)
    print("Patched successfully")
else:
    print("Could not find the block to replace")
