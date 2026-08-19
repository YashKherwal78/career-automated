"""
Point at a folder of job-post screenshots; runs each through the ingestion
pipeline in dry-run mode by default. This is the no-frontend entry point for
phase 1 (see docs/superpowers/specs/2026-08-18-google-forms-apply-pipeline-design.md) --
the user hands over a folder path and reviews backend/executions/<run_id>/
afterward.

Usage:
    python scripts/run_google_forms_batch.py --folder /path/to/screenshots --user-id <uuid> [--live]
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ingestion.screenshot_extractor import extract_from_image
from src.ingestion.pipeline import run_lead

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, help="Folder of screenshots to process")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--live", action="store_true", help="Submit for real (default: dry-run)")
    args = parser.parse_args()

    paths = [p for ext in IMAGE_EXTENSIONS for p in glob.glob(os.path.join(args.folder, f"*{ext}"))]
    print(f"Found {len(paths)} images in {args.folder}")

    for path in paths:
        lead = extract_from_image(path)
        if lead is None:
            print(f"SKIP  {path}: extraction failed or low-confidence")
            continue

        outcome = run_lead(lead, user_id=args.user_id, test_mode=not args.live)
        print(f"{outcome['status']:<20} {lead.company} / {lead.role}  -> {outcome.get('run_id')}")


if __name__ == "__main__":
    main()
