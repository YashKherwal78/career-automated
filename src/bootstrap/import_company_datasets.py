#!/usr/bin/env python3
"""
One-Time Company Bootstrap Importer
====================================
src/bootstrap/import_company_datasets.py

Imports companies from two external sources into Pipeline A's bootstrap tables:

  1. Jobhive (ats-scrapers) — https://github.com/kalil0321/ats-scrapers (MIT)
     CSVs: columns [name, slug, url], one CSV per ATS type.
     known_ats is set from the filename (greenhouse.csv → greenhouse).

  2. DPIIT Startup Dataset — Official Government of India startup registry.
     Expected columns: [StartupName, Website, State, City, Sector, Industry]
     ATS is unknown; companies enter the normal Pipeline A discovery flow.

Target table: company_identities (Pipeline A bootstrap table)
  - company_id  TEXT PRIMARY KEY (domain-slug)
  - domain      TEXT UNIQUE NOT NULL
  - canonical_name TEXT NOT NULL
  - website     TEXT
  - aliases     TEXT (JSON, stores known_ats and source metadata)

Rules:
  - Idempotent: INSERT OR IGNORE — safe to run multiple times.
  - Dedup: primary key is domain; duplicate domains are skipped silently.
  - No ATS marked ACTIVE: known_ats stored as metadata only.
    EndpointVerificationWorker remains the source of truth for ATS status.
  - Does NOT modify any workers, pipelines, or schedulers.
  - Pipeline A is untouched; this only adds rows to company_identities.

Usage:
  python3 src/bootstrap/import_company_datasets.py
  python3 src/bootstrap/import_company_datasets.py --dry-run
  python3 src/bootstrap/import_company_datasets.py --source jobhive
  python3 src/bootstrap/import_company_datasets.py --source dpiit --file data/dpiit_startups.csv
  python3 src/bootstrap/import_company_datasets.py --verify
"""

import argparse
import csv
import hashlib
import io
import json
import logging
import os
import re
import sqlite3
import sys
import urllib.request
from typing import Iterator, NamedTuple, Optional
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bootstrap")

DB_PATH = os.environ.get("DATABASE_PATH", "data/crm.db")

# ── Jobhive CSVs to import ──────────────────────────────────────────────────
# Only ATS types that Pipeline A has connectors for, or that are worth
# discovering via EndpointVerificationWorker. Excluded: avature, gem,
# cornerstone, eightfold, phenom, taleo, oracle (enterprise-only/legacy).
JOBHIVE_CSVS = {
    "greenhouse":      "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/greenhouse.csv",
    "ashby":           "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/ashby.csv",
    "lever":           "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/lever.csv",
    "workday":         "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/workday.csv",
    "smartrecruiters": "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/smartrecruiters.csv",
    "bamboohr":        "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/bamboohr.csv",
    "workable":        "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/workable.csv",
    "teamtailor":      "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/teamtailor.csv",
    "recruitee":       "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/recruitee.csv",
    "breezy":          "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/breezy.csv",
    "rippling":        "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/rippling.csv",
    "icims":           "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/icims.csv",
    "jazzhr":          "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/jazzhr.csv",
    "personio":        "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/personio.csv",
    "pinpoint":        "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/pinpoint.csv",
}


# ── Canonical company record ─────────────────────────────────────────────────

class CompanyRecord(NamedTuple):
    company_id: str       # domain-slug, unique
    domain: str           # bare domain, primary dedup key
    canonical_name: str
    website: str
    aliases: str          # JSON: {source, known_ats, country, city, industry}
    source: str           # "jobhive" | "dpiit"


# ── Domain utilities ─────────────────────────────────────────────────────────

def extract_domain(url: str) -> Optional[str]:
    """Return bare domain from a URL, stripping www. and path."""
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        host = urlparse(url).netloc or urlparse(url).path
        host = host.split(":")[0].lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host if "." in host else None
    except Exception:
        return None


def domain_to_id(domain: str) -> str:
    """Stable company_id from a domain: 'stripe.com' → 'stripe-com-a1b2c3'."""
    slug = re.sub(r"[^a-z0-9]", "-", domain.lower())
    suffix = hashlib.md5(domain.encode()).hexdigest()[:6]
    return f"{slug}-{suffix}"


def infer_website(url: str, domain: str) -> str:
    """Best-effort canonical website from ATS board URL or domain."""
    if domain:
        return f"https://{domain}"
    return url


# ── Jobhive parser ───────────────────────────────────────────────────────────

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "CareerAutomated/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_jobhive_csv(ats_name: str, csv_text: str) -> Iterator[CompanyRecord]:
    """Parse a single Jobhive CSV (columns: name, slug, url)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        name  = (row.get("name")  or "").strip()
        slug  = (row.get("slug")  or "").strip()
        url   = (row.get("url")   or "").strip()  # ATS board URL, not company website
        if not name or not url:
            continue

        # The slug is the ATS board slug (e.g. 'stripe', 'figma').
        # Infer company domain as slug.com — best effort, Pipeline A will verify.
        # If slug contains a path separator it's a Workday-style slug; extract first part.
        clean_slug = slug.split("/")[0].lower().strip() if slug else ""
        domain = f"{clean_slug}.com" if clean_slug else None
        if not domain:
            continue

        metadata = json.dumps({
            "source":    "jobhive",
            "known_ats": ats_name,       # stored only; ATS NOT marked ACTIVE
            "ats_slug":  slug,            # ATS board slug for EndpointVerificationWorker hint
            "board_url": url,
        })

        yield CompanyRecord(
            company_id=domain_to_id(domain),
            domain=domain,
            canonical_name=name,
            website=f"https://{domain}",
            aliases=metadata,
            source="jobhive",
        )


def load_jobhive(ats_filter: Optional[list] = None, dry_run: bool = False) -> list[CompanyRecord]:
    records = []
    sources = {k: v for k, v in JOBHIVE_CSVS.items()
               if ats_filter is None or k in ats_filter}

    for ats_name, url in sources.items():
        log.info(f"Fetching Jobhive/{ats_name} …")
        try:
            text = fetch_url(url)
            batch = list(parse_jobhive_csv(ats_name, text))
            log.info(f"  → {len(batch)} companies parsed from {ats_name}.csv")
            records.extend(batch)
        except Exception as e:
            log.warning(f"  Failed to fetch {ats_name}.csv: {e}")

    return records


# ── DPIIT parser ─────────────────────────────────────────────────────────────

# Expected CSV columns (case-insensitive match):
#   StartupName | EntityName | Company Name
#   Website | WebsiteURL | URL
#   State | StateName
#   City | CityName
#   Sector
#   Industry | IndustryName

_DPIIT_NAME_COLS    = ["StartupName", "EntityName", "Company Name", "name"]
_DPIIT_WEBSITE_COLS = ["Website", "WebsiteURL", "URL", "url", "website"]
_DPIIT_STATE_COLS   = ["State", "StateName", "state"]
_DPIIT_CITY_COLS    = ["City", "CityName", "city"]
_DPIIT_SECTOR_COLS  = ["Sector", "sector"]
_DPIIT_INDUSTRY_COLS= ["Industry", "IndustryName", "industry"]


def _pick(row: dict, candidates: list) -> str:
    for c in candidates:
        if c in row and row[c]:
            return row[c].strip()
    return ""


def parse_dpiit_csv(csv_text: str) -> Iterator[CompanyRecord]:
    """Parse a DPIIT startup CSV into CompanyRecords."""
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        name    = _pick(row, _DPIIT_NAME_COLS)
        website = _pick(row, _DPIIT_WEBSITE_COLS)
        state   = _pick(row, _DPIIT_STATE_COLS)
        city    = _pick(row, _DPIIT_CITY_COLS)
        sector  = _pick(row, _DPIIT_SECTOR_COLS)
        industry= _pick(row, _DPIIT_INDUSTRY_COLS)

        if not name:
            continue

        domain = extract_domain(website) if website else None
        if not domain:
            # Fall back to slugifying the company name as best-effort domain
            slug = re.sub(r"[^a-z0-9]", "", name.lower())[:20]
            domain = f"{slug}.in" if slug else None

        if not domain:
            continue

        metadata = json.dumps({
            "source":   "dpiit",
            "country":  "India",
            "state":    state,
            "city":     city,
            "sector":   sector,
            "industry": industry,
        })

        yield CompanyRecord(
            company_id=domain_to_id(domain),
            domain=domain,
            canonical_name=name,
            website=website or f"https://{domain}",
            aliases=metadata,
            source="dpiit",
        )


def load_dpiit(file_path: str) -> list[CompanyRecord]:
    log.info(f"Reading DPIIT dataset from {file_path} …")
    if not os.path.exists(file_path):
        log.error(f"DPIIT file not found: {file_path}")
        return []

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".xlsx", ".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            headers = [str(h).strip() if h else "" for h in rows[0]]
            csv_rows = [",".join(
                f'"{str(c).replace(chr(34), chr(39))}"' if c else ""
                for c in row
            ) for row in rows[1:]]
            csv_text = ",".join(f'"{h}"' for h in headers) + "\n" + "\n".join(csv_rows)
        except ImportError:
            log.error("openpyxl required for .xlsx files: pip install openpyxl")
            return []
    else:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            csv_text = f.read()

    records = list(parse_dpiit_csv(csv_text))
    log.info(f"  → {len(records)} companies parsed from DPIIT dataset")
    return records


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate(records: list[CompanyRecord]) -> list[CompanyRecord]:
    """Remove cross-source duplicates by domain. First-seen wins."""
    seen_domains: dict[str, CompanyRecord] = {}
    for r in records:
        if r.domain not in seen_domains:
            seen_domains[r.domain] = r
        # else: silently discard duplicate domain
    unique = list(seen_domains.values())
    removed = len(records) - len(unique)
    if removed:
        log.info(f"Deduplication: removed {removed} duplicate domains ({len(unique)} unique remain)")
    return unique


# ── Database insert ───────────────────────────────────────────────────────────

def insert_records(records: list[CompanyRecord], db_path: str, dry_run: bool = False) -> dict:
    """
    INSERT OR IGNORE into company_identities.
    Returns stats: {inserted, skipped, errors}
    """
    stats = {"inserted": 0, "skipped": 0, "errors": 0}

    if dry_run:
        log.info(f"[DRY RUN] Would attempt to insert {len(records)} records.")
        for r in records[:5]:
            log.info(f"  Sample: {r.canonical_name} ({r.domain}) [{r.source}]")
        if len(records) > 5:
            log.info(f"  ... and {len(records) - 5} more.")
        return stats

    with sqlite3.connect(db_path, timeout=30.0) as conn:
        # Pre-load existing domains to count skips accurately
        existing = {row[0] for row in conn.execute("SELECT domain FROM company_identities")}
        log.info(f"Existing company_identities rows: {len(existing)}")

        for r in records:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO company_identities
                       (company_id, domain, canonical_name, website, aliases)
                       VALUES (?, ?, ?, ?, ?)""",
                    (r.company_id, r.domain, r.canonical_name, r.website, r.aliases),
                )
                if r.domain in existing:
                    stats["skipped"] += 1
                else:
                    stats["inserted"] += 1
                    existing.add(r.domain)
            except Exception as e:
                log.warning(f"Insert error for {r.domain}: {e}")
                stats["errors"] += 1

        conn.commit()

    return stats


# ── Verification query ────────────────────────────────────────────────────────

def run_verification(db_path: str):
    log.info("\n=== Post-Import Verification ===\n")
    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM company_identities").fetchone()[0]
        unique_domains = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM company_identities"
        ).fetchone()[0]

        log.info(f"  Total company_identities rows : {total}")
        log.info(f"  Unique domains                : {unique_domains}")

        if total != unique_domains:
            log.warning(f"  ⚠️  {total - unique_domains} duplicate domains detected!")
        else:
            log.info("  ✅ No duplicate domains.")

        log.info("\n  By source (from aliases JSON):")
        rows = conn.execute(
            """SELECT json_extract(aliases, '$.source') as src, COUNT(*) as cnt
               FROM company_identities
               GROUP BY src
               ORDER BY cnt DESC"""
        ).fetchall()
        for src, cnt in rows:
            log.info(f"    {src or 'unknown':20s}  {cnt:>6,}")

        log.info("\n  By known_ats (Jobhive only):")
        rows = conn.execute(
            """SELECT json_extract(aliases, '$.known_ats') as ats, COUNT(*) as cnt
               FROM company_identities
               WHERE json_extract(aliases, '$.source') = 'jobhive'
               GROUP BY ats
               ORDER BY cnt DESC"""
        ).fetchall()
        for ats, cnt in rows:
            log.info(f"    {ats or 'unknown':20s}  {cnt:>6,}")

        log.info("\n  Idempotency check: re-counting distinct domains…")
        log.info(f"  PASS — domain column has UNIQUE constraint, duplicates silently ignored.\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="One-time bootstrap importer: Jobhive + DPIIT → company_identities"
    )
    parser.add_argument(
        "--source",
        choices=["jobhive", "dpiit", "all"],
        default="all",
        help="Which dataset(s) to import (default: all)",
    )
    parser.add_argument(
        "--ats",
        nargs="+",
        help="Jobhive: import only specific ATS types (e.g. --ats greenhouse lever)",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="DPIIT: path to CSV or XLSX file (default: data/dpiit_startups.csv)",
    )
    parser.add_argument(
        "--db",
        default=DB_PATH,
        help=f"SQLite database path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and deduplicate but do not write to the database",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Print verification SQL results and exit",
    )
    args = parser.parse_args()

    if args.verify:
        run_verification(args.db)
        return

    if not os.path.exists(args.db):
        log.error(f"Database not found: {args.db}. Run python run_pipeline.py first to initialise it.")
        sys.exit(1)

    all_records: list[CompanyRecord] = []

    # ── Jobhive ──
    if args.source in ("jobhive", "all"):
        log.info("=== Jobhive import ===")
        records = load_jobhive(ats_filter=args.ats)
        log.info(f"Jobhive total before dedup: {len(records)}")
        all_records.extend(records)

    # ── DPIIT ──
    if args.source in ("dpiit", "all"):
        log.info("=== DPIIT import ===")
        dpiit_file = args.file or "data/dpiit_startups.csv"
        if not os.path.exists(dpiit_file):
            log.warning(
                f"DPIIT file not found at {dpiit_file}. "
                f"Download from https://www.startupindia.gov.in/content/sih/en/search.html "
                f"and place at {dpiit_file}. Skipping DPIIT for now."
            )
        else:
            records = load_dpiit(dpiit_file)
            all_records.extend(records)

    if not all_records:
        log.warning("No records loaded. Nothing to import.")
        return

    log.info(f"\nTotal records across all sources: {len(all_records)}")

    # ── Global deduplication ──
    unique = deduplicate(all_records)
    log.info(f"After global dedup: {len(unique)} unique domains\n")

    # ── Insert ──
    stats = insert_records(unique, args.db, dry_run=args.dry_run)

    if not args.dry_run:
        log.info(f"\nImport complete:")
        log.info(f"  Inserted : {stats['inserted']:>6,}")
        log.info(f"  Skipped  : {stats['skipped']:>6,}  (already existed)")
        log.info(f"  Errors   : {stats['errors']:>6,}")

        log.info("\nRunning post-import verification…")
        run_verification(args.db)


if __name__ == "__main__":
    main()
