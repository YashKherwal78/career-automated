from src.crm.database import get_connection

class PriorityScheduler:
    def get_companies_to_scan(self, limit: int = 100) -> list:
        conn = get_connection()
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        # In a real scheduler, we would check last_scan and scan_priority_score
        # For example, priority > 100 gets scanned hourly (if last_scan < 1 hour ago)
        # For simplicity in this iteration, we just sort by scan_priority_score and get top N
        
        c.execute('''
            SELECT company_name, ats_provider, greenhouse_slug, lever_slug, ashby_slug, scan_priority_score 
            FROM company_intelligence_static 
            WHERE lifecycle_status != 'BROKEN'
            ORDER BY scan_priority_score DESC
            LIMIT ?
        ''', (limit,))
        
        companies = c.fetchall()
        conn.close()
        return companies

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
