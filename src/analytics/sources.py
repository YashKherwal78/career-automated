import sqlite3
from src.config.config import Config

def print_source_rankings():
    print("========================================")
    print(" SOURCE QUALITY RANKINGS ")
    print("========================================")
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # We aggregate by the 'source' column in the jobs table
    # And we join with leads to see if those jobs turned into emails, replies, or interviews.
    
    query = """
        SELECT 
            j.source,
            COUNT(j.id) as total_jobs,
            SUM(CASE WHEN j.quality_score > 0 THEN 1 ELSE 0 END) as high_quality,
            SUM(CASE WHEN l.hr_contacted = 1 OR l.founder_contacted = 1 THEN 1 ELSE 0 END) as outreach_sent,
            SUM(CASE WHEN l.hr_replied = 1 OR l.founder_replied = 1 THEN 1 ELSE 0 END) as replies,
            SUM(CASE WHEN l.interview_scheduled = 1 THEN 1 ELSE 0 END) as interviews
        FROM jobs j
        LEFT JOIN leads l ON j.id = l.job_id
        GROUP BY j.source
        ORDER BY interviews DESC, replies DESC, high_quality DESC, total_jobs DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"{'Source':<35} | {'Jobs':<5} | {'High Qual':<10} | {'Outreach':<8} | {'Replies':<7} | {'Interviews':<10}")
    print("-" * 90)
    
    for row in rows:
        source = str(row[0])[:34]
        jobs = row[1]
        hq = row[2]
        outreach = row[3]
        replies = row[4]
        interviews = row[5]
        print(f"{source:<35} | {jobs:<5} | {hq:<10} | {outreach:<8} | {replies:<7} | {interviews:<10}")
        
    print("========================================\n")
    conn.close()

if __name__ == "__main__":
    print_source_rankings()
