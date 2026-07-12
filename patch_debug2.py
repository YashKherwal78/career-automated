with open("src/discovery/pipeline/sync_session.py", "r") as f:
    text = f.read()
text = text.replace("self.stats[\"jobs_extracted\"] = len(canonical_jobs)", "self.stats[\"jobs_extracted\"] = len(canonical_jobs)\\n                    print(f'Raw jobs: {len(raw_jobs)}, Canonical jobs: {len(canonical_jobs)}')")
with open("src/discovery/pipeline/sync_session.py", "w") as f:
    f.write(text)
