import sqlite3
import datetime
import re
from src.config.config import Config

def get_role_counts(cursor, status_filter=None):
    query = "SELECT job_title FROM jobs"
    if status_filter:
        query += f" WHERE eligibility_status = '{status_filter}'"
        
    cursor.execute(query)
    titles = [row[0].lower() for row in cursor.fetchall()]
    
    counts = {
        "Associate Product Manager": 0,
        "Product Analyst": 0,
        "AI Product Manager": 0,
        "Product Operations": 0,
        "Business Analyst": 0,
        "Data Analyst": 0,
        "AI Engineer": 0,
        "ML Engineer": 0,
        "Software Engineer": 0
    }
    
    for title in titles:
        if re.search(r'\b(associate product manager|apm)\b', title): counts["Associate Product Manager"] += 1
        elif re.search(r'\b(product analyst)\b', title): counts["Product Analyst"] += 1
        elif re.search(r'\b(ai product manager)\b', title): counts["AI Product Manager"] += 1
        elif re.search(r'\b(product operations|product ops)\b', title): counts["Product Operations"] += 1
        elif re.search(r'\b(business analyst)\b', title): counts["Business Analyst"] += 1
        elif re.search(r'\b(data analyst)\b', title): counts["Data Analyst"] += 1
        elif re.search(r'\b(ai engineer)\b', title): counts["AI Engineer"] += 1
        elif re.search(r'\b(ml engineer|machine learning engineer)\b', title): counts["ML Engineer"] += 1
        elif re.search(r'\b(software engineer|swe)\b', title): counts["Software Engineer"] += 1
        
    return counts

def print_source_attribution(cursor):
    cursor.execute("SELECT source, job_title, eligibility_status FROM jobs")
    jobs = cursor.fetchall()
    
    sources = {}
    for source, title, elig in jobs:
        source_name = source or "Unknown"
        title = title.lower()
        if source_name not in sources:
            sources[source_name] = {"Total": 0, "SWE": 0, "Product": 0, "Data": 0, "AI": 0, "Eligible": 0}
            
        sources[source_name]["Total"] += 1
        if elig == "Eligible":
            sources[source_name]["Eligible"] += 1
            
        if re.search(r'\b(software engineer|swe|backend|frontend|fullstack)\b', title):
            sources[source_name]["SWE"] += 1
        elif re.search(r'\b(product|apm|business analyst)\b', title):
            sources[source_name]["Product"] += 1
        elif re.search(r'\b(data analyst|data scientist)\b', title):
            sources[source_name]["Data"] += 1
        elif re.search(r'\b(ai engineer|ml engineer|machine learning|applied ai)\b', title):
            sources[source_name]["AI"] += 1
            
    print("\n========================================")
    print(" SOURCE ATTRIBUTION ANALYTICS ")
    print("========================================")
    print(f"{'Source':<20} | {'Total':<5} | {'SWE':<5} | {'Prod':<5} | {'Data':<5} | {'AI':<5} | {'Conv %':<6}")
    print("-" * 75)
    for s, counts in sources.items():
        # Using "Eligible" rate as a proxy for Interview Conversion until the CRM handles state
        conv_rate = (counts["Eligible"] / counts["Total"] * 100) if counts["Total"] > 0 else 0
        print(f"{s[:19]:<20} | {counts['Total']:<5} | {counts['SWE']:<5} | {counts['Product']:<5} | {counts['Data']:<5} | {counts['AI']:<5} | {conv_rate:.1f}%")

def print_apify_analytics(cursor):
    # Attempt to query Apify Metrics if the table exists
    try:
        cursor.execute("SELECT SUM(calls_made), SUM(credits_consumed), SUM(cost_usd), SUM(contacts_found) FROM apify_metrics")
        row = cursor.fetchone()
        calls = row[0] or 0
        credits = row[1] or 0.0
        cost = row[2] or 0.0
        contacts = row[3] or 0
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        total_contacts = cursor.fetchone()[0] or 0
        
        cpc = (cost / contacts) if contacts > 0 else 0.0
        
        print("\n========================================")
        print(" APIFY ENRICHMENT ANALYTICS ")
        print("========================================")
        print(f"Total API Calls:        {calls}")
        print(f"Credits Consumed:       {credits:.3f}")
        print(f"Total Cost (USD):       ${cost:.3f}")
        print(f"Contacts Discovered:    {total_contacts}")
        print(f"Cost per Contact:       ${cpc:.3f}\n")
    except sqlite3.OperationalError:
        pass

def print_funnel_metrics():
    print("========================================")
    print(" RECRUITMENT FUNNEL ANALYTICS ")
    print("========================================")
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # 1. Total raw jobs
    cursor.execute("SELECT COUNT(*), SUM(duplicate_count) FROM jobs")
    row = cursor.fetchone()
    unique_jobs = row[0] or 0
    duplicates = row[1] or 0
    total_raw = unique_jobs + duplicates
    
    # 2. Eligibility Metrics
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE eligibility_status = 'Eligible'")
    eligible_jobs = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(eligibility_score) FROM jobs WHERE eligibility_status = 'Eligible'")
    avg_score = cursor.fetchone()[0] or 0
    
    print(f"Jobs Processed:         {total_raw}")
    print(f"Unique Jobs:            {unique_jobs}")
    print(f"Eligible Jobs:          {eligible_jobs}")
    print(f"Average Eligible Score: {avg_score:.1f}\n")
    
    # Role Distributions
    raw_counts = get_role_counts(cursor, None)
    eligible_counts = get_role_counts(cursor, 'Eligible')
    
    print("Role Distribution (Raw vs Eligible):")
    print(f"{'Role':<30} | {'Raw':<5} | {'Eligible':<5}")
    print("-" * 50)
    for role in raw_counts.keys():
        print(f"{role:<30} | {raw_counts[role]:<5} | {eligible_counts[role]:<5}")
        
    print_source_attribution(cursor)
    print_apify_analytics(cursor)
        
    print("\n========================================")
    print(" TOP 20 OPPORTUNITIES (RANKED) ")
    print("========================================")
    
    cursor.execute("""
        SELECT company_name, job_title, location, eligibility_score, ranking_score, recommended_resume
        FROM jobs 
        WHERE eligibility_status = 'Eligible' 
        ORDER BY ranking_score DESC 
        LIMIT 20
    """)
    top_20 = cursor.fetchall()
    
    print(f"{'Company':<15} | {'Role':<30} | {'Location':<20} | {'Elig':<4} | {'Rank':<4} | {'Resume':<15}")
    print("-" * 105)
    for row in top_20:
        company = str(row[0])[:14]
        title = str(row[1])[:29]
        loc = str(row[2])[:19]
        elig = row[3]
        rank = row[4]
        resume = str(row[5])
        print(f"{company:<15} | {title:<30} | {loc:<20} | {elig:<4} | {rank:<4} | {resume:<15}")
        
    print("========================================\n")
    
    # 5. Today's Queue
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT company, title, ranking_score, recommended_resume, queue_status 
        FROM application_queue 
        WHERE queue_date = ? AND queue_status != 'APPLIED' AND queue_status != 'SKIPPED'
        ORDER BY ranking_score DESC
    """, (today,))
    queue_jobs = cursor.fetchall()
    
    print("========================================")
    print(f" TODAY'S QUEUE ({len(queue_jobs)}/20) ")
    print("========================================")
    print(f"{'Company':<15} | {'Role':<30} | {'Rank':<4} | {'Resume':<15} | {'Status'}")
    print("-" * 90)
    for row in queue_jobs:
        company = str(row[0])[:14]
        title = str(row[1])[:29]
        rank = row[2]
        resume = str(row[3])
        status = str(row[4])
        print(f"{company:<15} | {title:<30} | {rank:<4} | {resume:<15} | {status}")
        
    print("========================================\n")
    
    conn.close()

if __name__ == "__main__":
    print_funnel_metrics()
