with open("scratch/workday_discovery_backfill.py", "r") as f:
    content = f.read()
content = content.replace("company_name FROM company_identities", "canonical_name FROM company_identities")
with open("scratch/workday_discovery_backfill.py", "w") as f:
    f.write(content)
