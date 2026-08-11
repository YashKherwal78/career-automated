"""
Entry point matching the actual real-world workflow: "I have a job
posting link (or apply_url) and I know the company — find the HR/
recruiter emails and store them." Bridges from a job already in
`normalized_jobs` (title, description, company_id) plus `company_master`
(company_name, domain when known) into the referral engine
(`run_referral_engine`), which discovers contacts, scores them, finds
real emails, and writes to `referral_contacts`.

Usage:
    python3 -m src.referrals.find_contacts_for_job --url "<apply_url>"
    python3 -m src.referrals.find_contacts_for_job --company "Acme Inc" --title "Software Engineer"
"""
from src.system.logger import setup_logger
logger = setup_logger('find_contacts_for_job')
import argparse
import sqlite3
from src.config.config import Config
from src.referrals.pipeline import run_referral_engine


def find_contacts_for_job_url(apply_url: str) -> bool:
    """Looks up a job already in normalized_jobs by its apply_url, resolves
    its company name/domain via company_master, and runs the referral
    engine for it. Returns False (with a logged reason) if the job isn't
    in the DB yet — this only works for jobs the discovery pipeline has
    already scraped, it doesn't fetch arbitrary external URLs."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT title, description, company_id FROM normalized_jobs WHERE apply_url = ? LIMIT 1",
        (apply_url,),
    )
    row = cur.fetchone()
    if not row:
        logger.info(f"No job found in normalized_jobs for apply_url={apply_url!r} — "
                    f"this only works for jobs already discovered by the pipeline.")
        conn.close()
        return False

    cur.execute("SELECT company_name, domain FROM company_master WHERE company_id = ? LIMIT 1", (row["company_id"],))
    company_row = cur.fetchone()
    conn.close()

    company_name = company_row["company_name"] if company_row else row["company_id"]
    company_domain = company_row["domain"] if company_row and company_row["domain"] else ""
    run_referral_engine(company_name, row["title"] or "", job_description=row["description"] or "", company_domain=company_domain)
    return True


def find_contacts_for_company(company_name: str, job_title: str = "", job_description: str = "") -> None:
    """Direct entry point when you already have the company name and role
    (no need for the job to be in normalized_jobs)."""
    run_referral_engine(company_name, job_title, job_description=job_description)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="apply_url of a job already in normalized_jobs")
    parser.add_argument("--company", help="Company name (used when --url isn't in the DB yet)")
    parser.add_argument("--title", default="", help="Job title (used with --company)")
    parser.add_argument("--description", default="", help="Job description text (used with --company)")
    args = parser.parse_args()

    if args.url:
        found = find_contacts_for_job_url(args.url)
        if not found and args.company:
            logger.info("Falling back to --company since the URL wasn't found in normalized_jobs.")
            find_contacts_for_company(args.company, args.title, args.description)
    elif args.company:
        find_contacts_for_company(args.company, args.title, args.description)
    else:
        parser.print_help()
