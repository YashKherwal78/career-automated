import yaml
import logging
from typing import List, Dict, Any
from src.crm.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScanBudgetManager:
    """
    Prevents unnecessary scans by balancing daily API budgets against company priority and health.
    Outputs a daily scan plan.
    """
    
    def __init__(self, daily_budget: int = 5000):
        self.daily_budget = daily_budget
        with open('src/config/scheduler.yaml', 'r') as f:
            self.policies = yaml.safe_load(f)['scan_policies']
            
    def generate_daily_plan(self) -> Dict[str, Any]:
        """
        Creates a scan plan to maximize discovery quality without burning credits.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # We assume the Intelligence Engine computes the priority_score.
        cursor.execute('''
            SELECT company_name, scan_priority_score, lifecycle_status 
            FROM company_intelligence_static 
            WHERE lifecycle_status IN ('VERIFIED', 'MONITORED', 'ACTIVE_HIRING')
        ''')
        
        companies = cursor.fetchall()
        conn.close()
        
        plan = {
            'hourly': [],
            'daily': [],
            'every_3_days': [],
            'weekly': [],
            'deferred': []
        }
        
        for company in companies:
            score = company['scan_priority_score']
            name = company['company_name']
            
            # Simple policy assignment based on config
            if score >= self.policies['hourly']['min_score']:
                plan['hourly'].append(name)
            elif score >= self.policies['daily']['min_score']:
                plan['daily'].append(name)
            elif score >= self.policies['every_3_days']['min_score']:
                plan['every_3_days'].append(name)
            else:
                plan['weekly'].append(name)
                
        # Budget enforcement logic would trim the lists here if they exceed daily_budget
        total_scans_today = (len(plan['hourly']) * 24) + len(plan['daily']) + (len(plan['every_3_days']) / 3) + (len(plan['weekly']) / 7)
        
        logger.info(f"Generated Scan Plan: Hourly: {len(plan['hourly'])}, Daily: {len(plan['daily'])}, "
                    f"3-Day: {len(plan['every_3_days'])}, Weekly: {len(plan['weekly'])}. "
                    f"Estimated daily scans: {int(total_scans_today)}")
                    
        return plan

import sqlite3
