from src.crm.database import get_connection

class CompanyIntelligenceEngine:
    def __init__(self):
        pass

    def compute_all(self):
        conn = get_connection()
        conn.row_factory = dict_factory
        c = conn.cursor()
        
        c.execute("SELECT * FROM company_intelligence_static")
        companies = c.fetchall()
        
        updates = []
        for comp in companies:
            self._compute_source_reliability(comp['company_name'], c)
            
            ai_rel = self._compute_ai_relevance(comp)
            pm_rel = self._compute_pm_relevance(comp)
            out_pri = self._compute_outreach_priority(ai_rel, pm_rel)
            app_pri = self._compute_application_priority(ai_rel, pm_rel)
            scan_pri = self._compute_scan_priority_score(ai_rel, pm_rel)
            
            updates.append((
                ai_rel, pm_rel, out_pri, app_pri, scan_pri, comp['company_name']
            ))
            
        # Update the database
        c.executemany('''
            UPDATE company_intelligence_static 
            SET ai_relevance = ?, pm_relevance = ?, outreach_priority = ?, 
                application_priority = ?, scan_priority_score = ?
            WHERE company_name = ?
        ''', updates)
        conn.commit()
        conn.close()
        print(f"Computed intelligence and reliability for {len(updates)} companies.")

    def _compute_source_reliability(self, company_name: str, cursor):
        """
        Dynamically computes the reliability score of the discovery sources for a company.
        In a full implementation, this would aggregate historical success metrics across the entire platform.
        """
        cursor.execute("SELECT source, confidence FROM company_discovery_sources WHERE company_name = ?", (company_name,))
        sources = cursor.fetchall()
        
        for source in sources:
            source_name = source['source']
            confidence = source['confidence']
            
            # Simple heuristic for demonstration:
            # If a source found it multiple times (confidence > 1), reliability goes up.
            # Base reliability is 0.5. Each additional find adds 0.1, up to 0.99.
            base_rel = 0.5
            if source_name.lower() == 'wellfound':
                base_rel = 0.8
            elif source_name.lower() == 'google search':
                base_rel = 0.7
                
            calc_rel = min(0.99, base_rel + (0.1 * (confidence - 1)))
            
            cursor.execute("UPDATE company_discovery_sources SET reliability_score = ? WHERE company_name = ? AND source = ?", (calc_rel, company_name, source_name))

    def _compute_ai_relevance(self, comp) -> int:
        score = 0
        ind = str(comp.get('industry', '')).lower()
        name = str(comp.get('company_name', '')).lower()
        if 'ai' in ind or 'artificial intelligence' in ind:
            score += 50
        if 'ai' in name:
            score += 20
        # AI startups from our specific github importer
        if comp.get('discovery_source') == 'github_ai':
            score += 80
        return min(score, 100)

    def _compute_pm_relevance(self, comp) -> int:
        score = 20 # Base line for any tech company
        ind = str(comp.get('industry', '')).lower()
        if 'saas' in ind or 'fintech' in ind or 'consumer' in ind:
            score += 40
        return min(score, 100)
        
    def _compute_outreach_priority(self, ai_rel, pm_rel) -> str:
        if ai_rel > 70 or pm_rel > 70:
            return "HIGH"
        if ai_rel > 40 or pm_rel > 40:
            return "MEDIUM"
        return "LOW"
        
    def _compute_application_priority(self, ai_rel, pm_rel) -> str:
        if ai_rel > 80:
            return "VERY HIGH"
        if pm_rel > 60:
            return "HIGH"
        return "LOW"
        
    def _compute_scan_priority_score(self, ai_rel, pm_rel) -> int:
        return int((ai_rel * 1.5) + pm_rel)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

if __name__ == "__main__":
    engine = CompanyIntelligenceEngine()
    engine.compute_all()
