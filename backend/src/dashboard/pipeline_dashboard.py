import os
import sys
import time

def show_dashboard():
    from src.api.db import get_connection
    conn = get_connection()
    try:
        def get_count(query):
            row = conn.execute(query).fetchone()
            if row is None:
                return 0
            if isinstance(row, tuple):
                return row[0]
            if hasattr(row, "keys"):
                # Handle dictionary-like rows
                vals = list(dict(row).values())
                return vals[0] if vals else 0
            return 0

        # Fetch status counts
        total_imported = get_count("SELECT COUNT(*) FROM company_identities")
        fast_path = get_count("SELECT COUNT(*) FROM company_identities WHERE lifecycle_state = 'FAST_PATH_MATCHED'")
        verification_pending = get_count("SELECT COUNT(*) FROM company_identities WHERE lifecycle_state = 'VERIFICATION_PENDING'")
        verified = get_count("SELECT COUNT(*) FROM company_identities WHERE lifecycle_state = 'VERIFIED'")
        crawling = get_count("SELECT COUNT(*) FROM company_identities WHERE lifecycle_state = 'CRAWLING'")
        active = get_count("SELECT COUNT(*) FROM company_identities WHERE lifecycle_state = 'ACTIVE'")
        
        # Stored jobs count
        jobs_count = get_count("SELECT COUNT(*) FROM normalized_jobs")
        
        # Calculate percentages
        fast_path_pct = round((fast_path / total_imported * 100), 1) if total_imported > 0 else 0.0
        verify_pending_pct = round((verification_pending / total_imported * 100), 1) if total_imported > 0 else 0.0
        verified_pct = round((verified / total_imported * 100), 1) if total_imported > 0 else 0.0

        print("=" * 40)
        print("      CareerAutomated Pipeline Dashboard")
        print("=" * 40)
        print(f"Imported       :  {total_imported:,}")
        print("      ↓")
        print(f"Discovery      :  {total_imported:,}  (100.0%)")
        print("      ↓")
        print(f"Fast Path      :  {fast_path:,}  ({fast_path_pct}%)")
        print("      ↓")
        print(f"Verification   :  {verification_pending:,}  ({verify_pending_pct}%)")
        print("      ↓")
        print(f"Verified       :  {verified:,}  ({verified_pct}%)")
        print("      ↓")
        print(f"Crawler Active :  {active:,}")
        print("      ↓")
        print(f"Normalized     :  {jobs_count:,} jobs")
        print("=" * 40)
    finally:
        conn.close()

if __name__ == "__main__":
    show_dashboard()
