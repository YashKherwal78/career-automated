from src.system.logger import setup_logger
logger = setup_logger('registry_generator')
import sqlite3
import pandas as pd
import requests
import re
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.config import Config

def init_registry_db():
    from src.crm.database import init_db
    init_db()

def slugify(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def verify_ats(slug):
    """Pings ATS providers to find if slug exists."""
    # Check Greenhouse
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=3)
        if r.status_code == 200:
            return "greenhouse", slug
    except: pass
    
    # Check Lever
    try:
        r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=3)
        if r.status_code == 200:
            return "lever", slug
    except: pass
    
    # Check Ashby
    try:
        r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=3)
        if r.status_code == 200:
            return "ashby", slug
    except: pass
    
    return None, None

def run():
    logger.info("--- Registry Generator: Building Final Registry ---")
    init_registry_db()
    conn = sqlite3.connect(Config.DATABASE_PATH)
    c = conn.cursor()
    
    # Clear old registry for clean run
    c.execute("DELETE FROM final_company_registry")
    
    companies_to_process = []
    
    # Source B: Curated
    curated = [
        "Razorpay", "CRED", "Groww", "PhonePe", "Zepto", "Meesho", "Swiggy", 
        "Zomato", "BrowserStack", "Postman", "Chargebee", "Innovaccer", "Darwinbox", 
        "Juspay", "Slice", "Pocket FM", "Porter", "Navi", "InMobi", "Rippling", 
        "Atlassian", "Microsoft", "Google"
    ]
    for comp in curated:
        companies_to_process.append({
            "name": comp,
            "priority": "P0",
            "source": "Curated Dream Companies",
            "freq": "Very frequent"
        })
        
    # Source A: IIT List
    try:
        df = pd.read_excel('iit_company_list.xlsx')
        iit_names = df['Company Name'].dropna().tolist()
        for comp in iit_names:
            if comp not in curated:
                companies_to_process.append({
                    "name": comp,
                    "priority": "P1",
                    "source": "IIT Placement List",
                    "freq": "Frequent"
                })
    except Exception as e:
        logger.info(f"Could not load IIT list: {e}")
        
    # Source C: Indian High-Growth (We'll just add some known ones as P1)
    high_growth = ["Unacademy", "Upstox", "Zerodha", "MoEngage", "CleverTap", "MindTickle", "Freshworks"]
    for comp in high_growth:
        if comp not in [c['name'] for c in companies_to_process]:
            companies_to_process.append({
                "name": comp,
                "priority": "P1",
                "source": "Indian High-Growth Startups",
                "freq": "Frequent"
            })
            
    logger.info(f"Total companies to evaluate: {len(companies_to_process)}")
    
    added = 0
    
    for comp_data in companies_to_process:
        slug = slugify(comp_data["name"])
        provider, valid_slug = verify_ats(slug)
        
        if not provider:
            # Try removing common suffixes
            slug2 = slug.replace("india", "").replace("inc", "").replace("technologies", "").replace("pvt", "").replace("ltd", "")
            if slug2 != slug:
                provider, valid_slug = verify_ats(slug2)
                
        # Some hardcoded overrides for big companies that have weird slugs
        if comp_data["name"].lower() == "razorpay":
            provider, valid_slug = "lever", "razorpay"
        elif comp_data["name"].lower() == "cred":
            provider, valid_slug = "lever", "cred"
        elif comp_data["name"].lower() == "zepto":
            provider, valid_slug = "greenhouse", "zepto"
        elif comp_data["name"].lower() == "meesho":
            provider, valid_slug = "lever", "meesho"
        elif comp_data["name"].lower() == "juspay":
            provider, valid_slug = "lever", "juspay"
            
        if provider:
            logger.info(f"[FOUND] {comp_data['name']} uses {provider} ({valid_slug})")
            c.execute('''
                INSERT OR IGNORE INTO final_company_registry 
                (company_name, ats_provider, ats_slug, priority, discovery_source, scan_frequency)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (comp_data["name"], provider, valid_slug, comp_data["priority"], comp_data["source"], comp_data["freq"]))
            added += 1
        else:
            # Insert anyway without ATS provider so it can be picked up by Pipeline B / manual later
            c.execute('''
                INSERT OR IGNORE INTO final_company_registry 
                (company_name, priority, discovery_source, scan_frequency)
                VALUES (?, ?, ?, ?)
            ''', (comp_data["name"], comp_data["priority"], comp_data["source"], comp_data["freq"]))
            
    conn.commit()
    conn.close()
    
    logger.info(f"--- Registry Generation Complete. Found {added} ATS providers. ---")

if __name__ == "__main__":
    run()
