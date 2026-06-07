import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()
client = ApifyClient(os.getenv("APIFY_API_KEY"))

# Get the last run of the actor
run = client.actor("hKByXkMQaC5Qt9UMN").last_run().get()
if run:
    dataset_id = getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))
    if not dataset_id and isinstance(run, dict):
        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
    print(f"Dataset ID: {dataset_id}")
    items = list(client.dataset(dataset_id).iterate_items())
    if items:
        print(f"Got {len(items)} items from dataset {dataset_id}")
        print("Keys:")
        print(list(items[0].keys()))
        print("\nFirst item:")
        print(json.dumps(items[0], indent=2))
    else:
        print("Dataset is empty.")
else:
    print("No runs found.")
