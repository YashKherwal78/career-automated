from src.system.logger import setup_logger
logger = setup_logger('yc_importer')
from src.crm.database import get_connection

YC_COMPANIES = [
    ("Airbnb", "airbnb", "greenhouse", "airbnb", False),
    ("DoorDash", "doordash", "greenhouse", "doordash", False),
    ("Instacart", "instacart", "greenhouse", "instacart", False),
    ("Reddit", "reddit", "greenhouse", "reddit", False),
    ("Dropbox", "dropbox", "greenhouse", "dropbox", False),
    ("Gusto", "gusto", "greenhouse", "gusto", False),
    ("Scale AI", "scaleai", "greenhouse", "scaleai", False),
    ("Coinbase", "coinbase", "greenhouse", "coinbase", False),
    ("Rippling", "rippling", "lever", "rippling", False),
    ("Deel", "deel", "lever", "deel", False),
]

def import_yc_companies():
    conn = get_connection()
    c = conn.cursor()
    count = 0
    for company_name, slug, ats, ats_slug, hiring_in_india in YC_COMPANIES:
        gh_slug = ats_slug if ats == "greenhouse" else None
        lever_slug = ats_slug if ats == "lever" else None
        
        try:
            c.execute('''
                INSERT OR IGNORE INTO company_intelligence_static 
                (company_name, website, ats_provider, greenhouse_slug, lever_slug, yc_batch, hiring_in_india)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (company_name, f"https://{slug}.com", ats, gh_slug, lever_slug, "Yes", hiring_in_india))
            
            c.execute('''
                INSERT OR IGNORE INTO hiring_intelligence_dynamic 
                (company_name) VALUES (?)
            ''', (company_name,))
            count += 1
        except Exception as e:
            logger.info(f"Failed to seed {company_name}: {e}")
            
    conn.commit()
    conn.close()
    logger.info(f"Successfully imported {count} YC companies.")
    
if __name__ == "__main__":
    import_yc_companies()
