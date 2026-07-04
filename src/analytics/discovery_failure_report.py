import sqlite3
import pandas as pd
from src.config.config import Config

DB_PATH = Config.DATABASE_PATH

def analyze_failure(jobs_count: int, ats_provider: str, greenhouse: str, lever: str, ashby: str) -> tuple:
    """Returns (Failure Reason, Next Action)"""
    if jobs_count > 0:
        return ("✅", "None")
        
    if pd.isna(ats_provider) or not ats_provider:
        return ("ATS not detected", "Detect ATS")
        
    ats_str = str(ats_provider).strip()
    if ats_str.lower() == 'unknown' or ats_str == '' or ats_str.lower() == 'nan':
        return ("ATS not detected", "Detect ATS")
        
    ats_lower = ats_str.lower()
    
    # Check if we support the provider but maybe slug is missing
    supported = ["greenhouse", "lever", "ashby", "wellfound"]
    if ats_lower in supported:
        # Check slugs
        if ats_lower == "greenhouse" and not greenhouse:
            return ("Missing Greenhouse Slug", "Find slug")
        if ats_lower == "lever" and not lever:
            return ("Missing Lever Slug", "Find slug")
        if ats_lower == "ashby" and not ashby:
            return ("Missing Ashby Slug", "Find slug")
        
        # If we have the slug but 0 jobs, it could be invalid slug or they just aren't hiring
        return ("0 jobs found (Invalid slug or frozen)", f"Verify {ats_lower} slug")
        
    # If we know the ATS but don't support it yet
    return (f"Provider missing: {ats_provider}", f"Build {ats_provider}")

def generate_discovery_failure_report(print_report=True):
    conn = sqlite3.connect(DB_PATH)
    
    # Get all P0/P1 companies
    query = """
    SELECT 
        c.company_name, 
        c.priority, 
        c.ats_provider,
        c.greenhouse_slug,
        c.lever_slug,
        c.ashby_slug,
        COUNT(j.id) as jobs_found
    FROM company_intelligence_static c
    LEFT JOIN jobs j ON lower(c.company_name) = lower(j.company_name)
    WHERE c.priority IN ('P0', 'P1')
    GROUP BY c.company_name
    ORDER BY c.priority ASC, jobs_found ASC, c.company_name ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    report_data = []
    
    # Track provider impact
    provider_impact = {}
    
    for _, row in df.iterrows():
        company = row['company_name']
        priority = row['priority']
        ats = row['ats_provider'] if not pd.isna(row['ats_provider']) else "Unknown"
        jobs = row['jobs_found']
        
        reason, action = analyze_failure(
            jobs, ats, row['greenhouse_slug'], row['lever_slug'], row['ashby_slug']
        )
        
        if jobs == 0 and "Provider missing" in reason:
            provider = ats.lower()
            if provider not in provider_impact:
                provider_impact[provider] = 0
            provider_impact[provider] += 1
            
        report_data.append({
            "Priority": priority,
            "Company": company,
            "ATS": ats,
            "Jobs": jobs,
            "Failure Reason": reason,
            "Next Action": action
        })
        
    report_df = pd.DataFrame(report_data)
    
    if print_report:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        # Sort by ROI (Providers blocking the most companies)
        impact_data = [{"Provider": k.title(), "Companies Blocked": v, "Estimated Jobs Lost": f"~{v * 8}"} for k, v in sorted(provider_impact.items(), key=lambda item: item[1], reverse=True)]
        impact_df = pd.DataFrame(impact_data)
        
        print("=== PROVIDER IMPACT REPORT (ROI) ===")
        print(impact_df.to_string(index=False))
        print("\n=== AUTO DEBUG QUEUE / FAILURE REPORT ===")
        # Filter out successful jobs for the debug queue
        debug_df = report_df[report_df['Jobs'] == 0].sort_values(by=['Priority', 'Company'])
        print(debug_df.to_string(index=False))
        
    return report_df

if __name__ == "__main__":
    generate_discovery_failure_report()
