import os
import sys
import sqlite3
import csv
import traceback

sys.path.append('.')

from src.api.db import get_connection

def import_csvs():
    conn = get_connection()
    directory = 'research/ats-scrapers-main/ats-companies'
    
    total_companies_imported = 0
    total_duplicates = 0
    
    try:
        for filename in os.listdir(directory):
            if not filename.endswith('.csv'):
                continue
                
            provider = filename[:-4]
            safe_provider = "".join([c if c.isalnum() else '_' for c in provider])
            file_path = os.path.join(directory, filename)
            
            print(f"Importing {filename} into registry_{safe_provider}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                imported_for_provider = 0
                dups_for_provider = 0
                
                for row in reader:
                    name = row.get('name')
                    slug = row.get('slug')
                    url = row.get('url')
                    
                    if not slug or not url:
                        continue
                        
                    # Generate a globally unique company_id
                    company_id = f"{safe_provider}_{slug}"
                    
                    try:
                        # 1. Insert into company_master (Idempotent)
                        conn.execute("""
                        INSERT INTO company_master (company_id, company_name)
                        VALUES (?, ?)
                        ON CONFLICT(company_id) DO NOTHING
                        """, (company_id, name))
                        
                        # 2. Insert into registry_{provider} (Idempotent)
                        cursor = conn.execute(f"""
                        INSERT INTO registry_{safe_provider} (company_id, company_name, endpoint, priority)
                        VALUES (?, ?, ?, 'MEDIUM')
                        ON CONFLICT(company_id) DO NOTHING
                        """, (company_id, name, url))
                        
                        # If a row was inserted into registry, also insert its state
                        if cursor.rowcount > 0:
                            conn.execute(f"""
                            INSERT INTO registry_{safe_provider}_state (company_id, status)
                            VALUES (?, 'QUEUED')
                            ON CONFLICT(company_id) DO NOTHING
                            """, (company_id,))
                            imported_for_provider += 1
                            total_companies_imported += 1
                        else:
                            dups_for_provider += 1
                            total_duplicates += 1
                            
                    except sqlite3.Error as e:
                        print(f"Database error for {company_id}: {e}")
                        
                print(f"  -> Imported: {imported_for_provider}, Duplicates skipped: {dups_for_provider}")
                
        conn.commit()
        print(f"\nImport complete! Total imported: {total_companies_imported}, Total duplicates: {total_duplicates}")
        
    except Exception as e:
        print(f"Error during import: {e}")
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import_csvs()
