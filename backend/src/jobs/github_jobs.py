from src.system.logger import setup_logger
logger = setup_logger('github_jobs')
import requests
import re
from datetime import datetime

import base64
import time

QUERIES = [
    '"product manager jobs"',
    '"associate product manager jobs"',
    '"product analyst jobs"',
    '"business analyst jobs"',
    '"growth analyst jobs"',
    '"new grad software engineer"'
]

def fetch_github_jobs():
    """
    Fetches job listings from dynamically discovered GitHub repositories via Search API.
    """
    all_jobs = []
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    seen_repos = set()
    
    for query in QUERIES:
        logger.info(f"Searching GitHub for repos matching: {query}")
        try:
            # Search for repos that contain these terms in their README
            search_url = f"https://api.github.com/search/code?q={query}+in:file+filename:README.md&per_page=5"
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                items = response.json().get('items', [])
                for item in items:
                    repo_name = item['repository']['full_name']
                    
                    if repo_name in seen_repos:
                        continue
                    seen_repos.add(repo_name)
                    
                    logger.info(f"-> Found promising repo: {repo_name}")
                    
                    # Fetch the raw README content
                    raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/README.md"
                    readme_res = requests.get(raw_url)
                    if readme_res.status_code != 200:
                        raw_url = f"https://raw.githubusercontent.com/{repo_name}/master/README.md"
                        readme_res = requests.get(raw_url)
                        
                    if readme_res.status_code == 200:
                        jobs = parse_markdown_table(readme_res.text, repo_name)
                        all_jobs.extend(jobs)
                        logger.info(f"   Extracted {len(jobs)} jobs from {repo_name}")
            else:
                logger.info(f"GitHub Search API rate limit or error: {response.status_code}")
                
            # Respect rate limit (10 req / min for unauthenticated search)
            time.sleep(6)
            
        except Exception as e:
            logger.info(f"Error executing GitHub search for {query}: {e}")
            
    # As a fallback and safety measure, we'll explicitly pull the core repos just in case 
    # search API misses them.
    core_repos = [
        "SimplifyJobs/New-Grad-Positions",
        "SimplifyJobs/Summer2024-Internships",
        "SpeedyApply/2026-AI-College-Jobs"
    ]
    
    for repo_name in core_repos:
        if repo_name in seen_repos:
            continue
        logger.info(f"Fetching core fallback repo: {repo_name}...")
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/README.md"
        res = requests.get(raw_url)
        if res.status_code == 200:
            jobs = parse_markdown_table(res.text, repo_name)
            all_jobs.extend(jobs)
            logger.info(f"   Extracted {len(jobs)} jobs from {repo_name}")
            
    return all_jobs

from bs4 import BeautifulSoup

def parse_markdown_table(markdown_text: str, source_name: str):
    """
    Parses both HTML tables and raw Markdown tables.
    """
    jobs = []
    
    soup = BeautifulSoup(markdown_text, 'html.parser')
    tables = soup.find_all('table')
    
    if tables:
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    company_col = cols[0]
                    role_col = cols[1]
                    location_col = cols[2]
                    apply_col = cols[3]
                    
                    # Check for closed jobs
                    if "🔒" in row.text:
                        continue
                        
                    company = company_col.text.strip()
                    title = role_col.text.strip()
                    location = location_col.text.strip()
                    
                    # Extract URL from the apply column (first link usually)
                    job_url = ""
                    apply_links = apply_col.find_all('a')
                    if apply_links:
                        job_url = apply_links[0].get('href', '')
                    
                    if not job_url:
                        # Sometimes the company name has the link
                        comp_links = company_col.find_all('a')
                        if comp_links:
                            job_url = comp_links[0].get('href', '')
                            
                    if company and title and job_url:
                        jobs.append({
                            "company_name": company,
                            "job_title": title,
                            "location": location,
                            "job_url": job_url,
                            "job_description": f"Fetched from {source_name}. Visit link for details.",
                            "source": f"GitHub ({source_name})"
                        })
    else:
        # Fallback for raw markdown tables like | Company | Role | Location | ... |
        lines = markdown_text.split('\n')
        in_table = False
        for line in lines:
            line = line.strip()
            if line.startswith('|') and ('Company' in line or '---' in line):
                in_table = True
                continue
            
            if in_table and line.startswith('|'):
                cols = [c.strip() for c in line.split('|')]
                if len(cols) >= 5: # [empty, company, role, location, link...]
                    company_col = cols[1]
                    role_col = cols[2]
                    location_col = cols[3]
                    link_col = cols[4]
                    
                    company = extract_text_from_md_link(company_col)
                    if not company or company == 'Company': continue
                    title = extract_text_from_md_link(role_col)
                    location = location_col
                    
                    job_url = extract_url_from_md_link(link_col)
                    if not job_url:
                        job_url = extract_url_from_md_link(company_col)
                        
                    if company and title and job_url and "🔒" not in line:
                        jobs.append({
                            "company_name": company,
                            "job_title": title,
                            "location": location,
                            "job_url": job_url,
                            "job_description": f"Fetched from {source_name}. Visit link for details.",
                            "source": f"GitHub ({source_name})"
                        })

    return jobs

def extract_text_from_md_link(md_string: str):
    # Extracts "Google" from "[Google](https://...)" or just returns "Google"
    match = re.search(r'\[([^\]]+)\]', md_string)
    if match:
        return match.group(1).replace('*', '').strip()
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', '', md_string)
    return clean.replace('*', '').strip()

def extract_url_from_md_link(md_string: str):
    match = re.search(r'\((https?://[^\)]+)\)', md_string)
    if match:
        return match.group(1)
    
    # Check for raw href
    match = re.search(r'href="([^"]+)"', md_string)
    if match:
        return match.group(1)
        
    return ""

if __name__ == "__main__":
    jobs = fetch_github_jobs()
    logger.info(f"Total jobs extracted: {len(jobs)}")
    if jobs:
        logger.info(f"Sample: {jobs[0]}")
