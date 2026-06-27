import sys
import argparse
from src.crm.database import get_connection

def import_manual_company(name, website, ats, slug, hiring_in_india=False):
    conn = get_connection()
    c = conn.cursor()
    gh_slug = slug if ats == "greenhouse" else None
    lever_slug = slug if ats == "lever" else None
    ashby_slug = slug if ats == "ashby" else None
    
    try:
        c.execute('''
            INSERT OR IGNORE INTO company_intelligence_static 
            (company_name, website, ats_provider, greenhouse_slug, lever_slug, ashby_slug, hiring_in_india)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, website, ats, gh_slug, lever_slug, ashby_slug, hiring_in_india))
        
        c.execute('''
            INSERT OR IGNORE INTO hiring_intelligence_dynamic 
            (company_name) VALUES (?)
        ''', (name,))
        
        conn.commit()
        print(f"Successfully imported {name} ({ats}: {slug})")
    except Exception as e:
        print(f"Failed to insert {name}: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually import a company into the registry")
    parser.add_argument("--name", required=True, help="Company Name")
    parser.add_argument("--website", required=True, help="Company Website URL")
    parser.add_argument("--ats", required=True, choices=["greenhouse", "lever", "ashby"], help="ATS Provider")
    parser.add_argument("--slug", required=True, help="ATS Slug")
    parser.add_argument("--hiring-in-india", action="store_true", help="Is the company hiring in India?")
    
    args = parser.parse_args()
    import_manual_company(args.name, args.website, args.ats, args.slug, args.hiring_in_india)
