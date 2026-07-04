import time
import schedule
from typing import Callable

class DiscoveryScheduler:
    """
    Time-based scheduler for Discovery runs.
    Ensures Official ATS runs frequently (every 2 hours), while Search Connectors run less often (every 6 hours).
    """
    
    @staticmethod
    def run_official_discovery(job: Callable):
        schedule.every(2).hours.do(job)
        print("Scheduled Official Discovery every 2 hours.")

    @staticmethod
    def run_search_discovery(job: Callable):
        schedule.every(6).hours.do(job)
        print("Scheduled Search Discovery every 6 hours.")
        
    @staticmethod
    def run_company_discovery(job: Callable):
        schedule.every(12).hours.do(job)
        print("Scheduled Company Discovery every 12 hours.")

    @staticmethod
    def start():
        print("Scheduler started. Waiting for jobs...")
        while True:
            schedule.run_pending()
            time.sleep(60)
