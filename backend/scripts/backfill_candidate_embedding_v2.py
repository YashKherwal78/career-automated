"""
Backfills user_career_profiles.embedding_v2 (nomic-embed-text-v1.5,
migration 045) for profiles that existed before the profile-save
endpoints started computing it automatically. Small volume (one row per
user), so this just runs to completion in one pass rather than needing
a loop script like the job-side backfills.

Usage: python3 scripts/backfill_candidate_embedding_v2.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.repositories.job.repository import JobRepository  # noqa: E402
from src.discovery.embeddings import embed_text_v2_query, candidate_embedding_text  # noqa: E402

if __name__ == "__main__":
    repo = JobRepository()
    updated = 0
    while True:
        rows = repo.get_candidate_ids_missing_embedding_v2(limit=50)
        if not rows:
            break
        for row in rows:
            profile_data = row["profile_data"]
            if isinstance(profile_data, str):
                try:
                    profile_data = json.loads(profile_data)
                except Exception:
                    profile_data = {}
            try:
                vec = embed_text_v2_query(candidate_embedding_text(profile_data or {}))
                repo.store_candidate_embedding_v2(row["user_id"], vec)
                updated += 1
            except Exception as e:
                print(f"ERROR user_id={row['user_id']}: {e}")
        print(f"updated {updated} profiles so far")
    print(f"done, {updated} total")
