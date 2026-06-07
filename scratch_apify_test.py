import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

API_KEY = os.getenv("APIFY_API_KEY")
if not API_KEY:
    print("Error: APIFY_API_KEY not found in environment.")
    exit(1)

client = ApifyClient(API_KEY)
actor_id = "hKByXkMQaC5Qt9UMN"

print(f"Starting Apify actor {actor_id} for a test scrape of 5 jobs...")

# We need to construct the input for this specific actor. 
# "hKByXkMQaC5Qt9UMN" appears to be a LinkedIn Jobs Scraper.
run_input = {
    "urls": ["https://www.linkedin.com/jobs/search/?keywords=AI%20Engineer&location=Remote"],
    "maxItems": 5
}

try:
    run = client.actor(actor_id).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    print(f"\nScraped {len(items)} items. Schema of first item:")
    if items:
        print(json.dumps(items[0], indent=2))
        
        # Verify required fields
        required_fields = ["company_name", "job_title", "job_description", "job_url", "location", "posted_date"]
        # The actor might return them under different keys, e.g., "company", "title", "description", "url", "location", "postedAt"
        
        found_keys = list(items[0].keys())
        print(f"\nFound keys: {found_keys}")
    else:
        print("No items returned.")
except Exception as e:
    print(f"Error running Apify test: {e}")
