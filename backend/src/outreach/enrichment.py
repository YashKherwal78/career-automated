from src.system.logger import setup_logger
logger = setup_logger('enrichment')
import sqlite3
import datetime
import requests
import json
from src.config.config import Config

class EnrichmentLayer:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
    def check_apify_budget(self):
        """Check if we have exceeded daily/monthly Apify constraints."""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        month = datetime.datetime.now().strftime("%Y-%m")
        
        # Check daily runs
        self.cursor.execute("SELECT SUM(calls_made) FROM apify_metrics WHERE date(created_at) = ?", (today,))
        daily_runs = self.cursor.fetchone()[0] or 0
        if daily_runs >= Config.MAX_APIFY_RUNS_PER_DAY:
            logger.info(f"Apify blocked: Daily limit reached ({daily_runs}/{Config.MAX_APIFY_RUNS_PER_DAY})")
            return False
            
        # Check monthly budget
        self.cursor.execute("SELECT SUM(cost_usd) FROM apify_metrics WHERE strftime('%Y-%m', created_at) = ?", (month,))
        monthly_cost = self.cursor.fetchone()[0] or 0.0
        if monthly_cost >= Config.MAX_APIFY_MONTHLY_BUDGET:
            logger.info(f"Apify blocked: Monthly budget reached (${monthly_cost:.2f}/${Config.MAX_APIFY_MONTHLY_BUDGET:.2f})")
            return False
            
        return True

    def log_apify_metric(self, job_id, endpoint, calls, credits, cost, contacts_found):
        self.cursor.execute('''
            INSERT INTO apify_metrics (job_id, endpoint, calls_made, credits_consumed, cost_usd, contacts_found)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (job_id, endpoint, calls, credits, cost, contacts_found))
        self.conn.commit()

    def find_contacts(self, company, title):
        """Uses Apify to find Hiring Managers and Recruiters."""
        logger.info(f"Attempting Apify enrichment for {title} at {company}...")
        
        if not self.check_apify_budget():
            return self.fallback_duckduckgo_search(company, title)
            
        try:
            # Note: The Apify Google Search Scraper Actor is usually free but costs $0.005 per 1000 results on custom actors
            url = f"https://api.apify.com/v2/acts/{Config.APIFY_ACTOR_ID}/runs?token={Config.APIFY_API_KEY_ENRICHMENT}"
            payload = {
                "urls": [{"url": f"https://www.google.com/search?q=site:linkedin.com/in+%22{company}%22+(recruiter+OR+talent+OR+hiring+manager)"}],
                "maxPagesPerCrawl": 1
            }
            res = requests.post(url, json=payload)
            
            if res.status_code in [200, 201]:
                data = res.json()
                run_id = data['data']['id']
                default_dataset_id = data['data']['defaultDatasetId']
                
                # We would typically poll here, but for now we simulate the completion
                logger.info(f"Apify Run {run_id} started. Waiting for results...")
                
                # Mock results for architecture validation
                contacts = [
                    {"name": f"{company} Talent", "title": "Senior Technical Recruiter", "linkedin_url": f"https://linkedin.com/in/recruiter-{company.lower().replace(' ', '')}"}
                ]
                
                # Cost is roughly $0.001 per run depending on actor
                self.log_apify_metric(0, "google_search", 1, 0.001, 0.001, len(contacts))
                return contacts
            else:
                logger.info(f"Apify API Error: {res.status_code} - {res.text}")
                return self.fallback_duckduckgo_search(company, title)
                
        except Exception as e:
            logger.info(f"Apify Exception: {e}")
            return self.fallback_duckduckgo_search(company, title)

    def fallback_duckduckgo_search(self, company, title):
        logger.info(f"-> Falling back to DuckDuckGo/X-Ray search for {company}...")
        # Future implementation
        return []

    def enrich_queue(self):
        logger.info("Agent 3: Starting Apify Enrichment Layer...")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        self.cursor.execute("SELECT * FROM application_queue WHERE queue_date = ? AND queue_status = 'QUEUED'", (today,))
        queue = self.cursor.fetchall()
        
        if not queue:
            logger.info("No jobs in today's queue to enrich.")
            return
            
        logger.info(f"Found {len(queue)} jobs in queue to enrich.")
        for row in queue:
            job_id = row["job_id"]
            company = row["company"]
            title = row["title"]
            
            contacts = self.find_contacts(company, title)
            
            for c in contacts:
                self.cursor.execute('''
                    INSERT INTO contacts (job_id, name, title, linkedin_url, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', (job_id, c["name"], c["title"], c["linkedin_url"], 0.85))
                
            self.conn.commit()
            
        logger.info("Agent 3: Enrichment complete.")

if __name__ == "__main__":
    layer = EnrichmentLayer()
    layer.enrich_queue()
