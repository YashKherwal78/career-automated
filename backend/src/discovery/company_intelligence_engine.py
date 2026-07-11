import logging
from src.crm.database import get_connection
from src.discovery.event_bus import event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompanyIntelligenceEngine:
    """
    Computes priority scores, relevance, and assigns scan frequencies.
    Listens to CompanyEnrichedEvent and ATSDetectedEvent to trigger scoring.
    """
    def __init__(self):
        event_bus.subscribe('CompanyEnrichedEvent', self.handle_company_enriched)
        event_bus.subscribe('ATSDetectedEvent', self.handle_ats_detected)
        
    def handle_company_enriched(self, payload: dict):
        self._score_company(payload.get('company_name'))
        
    def handle_ats_detected(self, payload: dict):
        self._score_company(payload.get('company_name'))

    def compute_all(self):
        conn = get_connection()
        conn.row_factory = self._dict_factory
        c = conn.cursor()
        c.execute("SELECT company_name FROM company_intelligence_static")
        companies = [row["company_name"] for row in c.fetchall()]
        conn.close()
        for name in companies:
            self._score_company(name)

    def _score_company(self, company_name: str):
        if not company_name:
            return
            
        conn = get_connection()
        conn.row_factory = self._dict_factory
        c = conn.cursor()
        
        c.execute("SELECT * FROM company_intelligence_static WHERE company_name = ?", (company_name,))
        comp = c.fetchone()
        
        if not comp:
            conn.close()
            return
            
        ai_rel = self._compute_ai_relevance(comp)
        pm_rel = self._compute_pm_relevance(comp)
        founder_prob = self._compute_founder_office_probability(comp)
        india_prob = self._compute_india_hiring_probability(comp)
        
        out_pri = self._compute_outreach_priority(ai_rel, pm_rel, founder_prob)
        app_pri = self._compute_application_priority(ai_rel, pm_rel, founder_prob)
        scan_pri = self._compute_scan_priority_score(ai_rel, pm_rel, india_prob)
        
        scan_freq = self._assign_scan_frequency(scan_pri)
        
        c.execute('''
            UPDATE company_intelligence_static 
            SET ai_relevance = ?, pm_relevance = ?, founder_office_probability = ?, 
                hiring_in_india = ?, outreach_priority = ?, application_priority = ?, 
                scan_priority_score = ?, scan_frequency = ?
            WHERE company_name = ?
        ''', (ai_rel, pm_rel, founder_prob, 1 if india_prob > 50 else 0, out_pri, app_pri, scan_pri, scan_freq, company_name))
        conn.commit()
        conn.close()
        
        logger.info(f"Intelligence Engine scored {company_name}: Priority {scan_pri}, Freq: {scan_freq}")
        event_bus.publish('CompanyScoredEvent', {'company_name': company_name, 'scan_priority_score': scan_pri})

    def _compute_ai_relevance(self, comp) -> int:
        score = 0
        ind = str(comp.get('industry', '')).lower()
        name = str(comp.get('company_name', '')).lower()
        if 'ai' in ind or 'artificial intelligence' in ind:
            score += 50
        if 'ai' in name:
            score += 20
        if comp.get('discovery_source') == 'github_ai':
            score += 80
        return min(score, 100)

    def _compute_pm_relevance(self, comp) -> int:
        score = 20
        ind = str(comp.get('industry', '')).lower()
        if 'saas' in ind or 'fintech' in ind or 'consumer' in ind:
            score += 40
        return min(score, 100)
        
    def _compute_founder_office_probability(self, comp) -> float:
        score = 10.0
        # Startups early stage are more likely to have founder's office
        funding = str(comp.get('funding_stage', '')).lower()
        if 'seed' in funding or 'series a' in funding or 'yc' in str(comp.get('yc_batch', '')).lower():
            score += 60.0
        return min(score, 100.0)
        
    def _compute_india_hiring_probability(self, comp) -> float:
        score = 10.0
        hq = str(comp.get('headquarters', '')).lower()
        if 'india' in hq or 'bangalore' in hq or 'bengaluru' in hq or 'delhi' in hq:
            score += 80.0
        if comp.get('remote_hiring'):
            score += 30.0
        return min(score, 100.0)

    def _compute_outreach_priority(self, ai_rel, pm_rel, founder_prob) -> str:
        if ai_rel > 70 or pm_rel > 70 or founder_prob > 70:
            return "HIGH"
        if ai_rel > 40 or pm_rel > 40:
            return "MEDIUM"
        return "LOW"
        
    def _compute_application_priority(self, ai_rel, pm_rel, founder_prob) -> str:
        if ai_rel > 80:
            return "VERY HIGH"
        if pm_rel > 60 or founder_prob > 60:
            return "HIGH"
        return "LOW"
        
    def _compute_scan_priority_score(self, ai_rel, pm_rel, india_prob) -> int:
        return int((ai_rel * 1.0) + (pm_rel * 0.5) + (india_prob * 0.5))
        
    def _assign_scan_frequency(self, scan_pri: int) -> str:
        if scan_pri >= 90:
            return "hourly"
        elif scan_pri >= 75:
            return "daily"
        elif scan_pri >= 50:
            return "every_3_days"
        return "weekly"

    @staticmethod
    def compute_dynamic_health_score(company_name: str) -> float:
        """
        Computes the company health score dynamically on demand.
        Factors: recent hiring velocity, ATS uptime, intelligence freshness.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
            SELECT active_job_count, consecutive_failures, last_successful_sync 
            FROM hiring_intelligence_dynamic WHERE company_name = ?
        ''', (company_name,))
        dyn = c.fetchone()
        conn.close()
        
        health = 100.0
        if dyn:
            failures = dyn['consecutive_failures']
            if failures > 0:
                health -= (failures * 10)
            
            # If no recent successful sync
            # Note: would calculate days since last_successful_sync in real impl
                
        return max(0.0, min(health, 100.0))
        
    def _dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

if __name__ == "__main__":
    # Test
    engine = CompanyIntelligenceEngine()
