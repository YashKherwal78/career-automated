import logging
from typing import List, Dict
from src.crm.database import get_connection
from src.discovery.scan_budget_manager import ScanBudgetManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriorityScheduler:
    """
    Yields target companies for the Job Discovery Engine based on their dynamic priority, 
    assigned scan frequency, and the daily scan budget.
    """
    def __init__(self):
        self.budget_manager = ScanBudgetManager()

    def get_companies_to_scan(self, limit: int = 100) -> List[Dict]:
        daily_plan = self.budget_manager.generate_daily_plan()
        
        # Flatten the plan based on urgency
        scheduled_names = []
        scheduled_names.extend(daily_plan['hourly'])
        scheduled_names.extend(daily_plan['daily'])
        scheduled_names.extend(daily_plan['every_3_days'])
        scheduled_names.extend(daily_plan['weekly'])
        
        if not scheduled_names:
            return []
            
        # In a real implementation, we would query the database checking if `last_scan` 
        # is older than the configured interval for their frequency string.
        # Here we just fetch the top 'limit' companies from the schedule that are VERIFIED or MONITORED.
        
        conn = get_connection()
        conn.row_factory = self._dict_factory
        c = conn.cursor()
        
        # We can just fetch all companies in the schedule, ordered by priority
        placeholders = ','.join('?' * len(scheduled_names))
        
        c.execute(f'''
            SELECT company_name, ats_provider, greenhouse_slug, lever_slug, ashby_slug, careers_url
            FROM company_intelligence_static 
            WHERE company_name IN ({placeholders}) 
            AND lifecycle_status IN ('VERIFIED', 'MONITORED', 'ACTIVE_HIRING')
            ORDER BY scan_priority_score DESC
            LIMIT ?
        ''', (*scheduled_names, limit))
        
        companies = c.fetchall()
        conn.close()
        
        return companies

    def _dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
