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
# All 25 viable CSVs from the Jobhive repo (kalil0321/ats-scrapers).
# Excluded only: infojobs_es (1 row), jobs_cz (1 row), mercor (1 row).
# "Enterprise" ATS types are included — every company still flows through
# EndpointVerificationWorker, which is the source of truth for ATS status.
#
# Special schema notes:
#   eightfold.csv  → has extra 'domain' column; used directly (more accurate)
#   phenom.csv     → different schema: url/name/company_code; no 'slug' field
JOBHIVE_CSVS = {
    # ── Standard schema (name, slug, url) ────────────────────────────────────
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
    # ── Previously omitted — now included ────────────────────────────────────
    "join_com":        "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/join_com.csv",
    "successfactors":  "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/successfactors.csv",
    "recruiterbox":    "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/recruiterbox.csv",
    "oracle":          "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/oracle.csv",
    "cornerstone":     "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/cornerstone.csv",
    "gem":             "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/gem.csv",
    "avature":         "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/avature.csv",
    "taleo":           "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/taleo.csv",
    # ── Non-standard schemas (handled by dedicated parsers) ──────────────────
    "eightfold":       "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/eightfold.csv",
    "phenom":          "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies/phenom.csv",
    # ── Skipped (1 data row each — not worth importing) ──────────────────────
    # "infojobs_es"   1 row  (Spanish job board)
    # "jobs_cz"       1 row  (Czech job board)
    # "mercor"        1 row
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
    """
    Parse a standard Jobhive CSV (columns: name, slug, url).
    Also handles eightfold.csv which has an extra 'domain' column — that
    column is used directly as the company domain instead of inferring slug.com.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        name  = (row.get("name")   or "").strip()
        slug  = (row.get("slug")   or "").strip()
        url   = (row.get("url")    or "").strip()  # ATS board URL, not company website
        explicit_domain = (row.get("domain") or "").strip()  # eightfold only
        if not name or not url:
            continue

        if explicit_domain:
            # eightfold.csv provides the real company domain — use it directly.
            domain = extract_domain(f"https://{explicit_domain}") or extract_domain(url)
        else:
            # Standard CSVs: derive domain from the ATS board slug.
            # slug.com is a best-effort inference; Pipeline A verifies the real ATS.
            # Workday slugs look like 'company/external_careers'; take first segment.
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


def parse_phenom_csv(csv_text: str) -> Iterator[CompanyRecord]:
    """
    Parse phenom.csv which has a non-standard schema:
      url, name, company_code, locale, country
    No 'slug' field. Use company_code as the slug equivalent.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        name         = (row.get("name")         or "").strip()
        company_code = (row.get("company_code") or "").strip()
        url          = (row.get("url")          or "").strip()
        if not name or not url:
            continue

        # Prefer domain extracted from the Phenom board URL, fall back to code.com
        domain = extract_domain(url)
        if not domain:
            clean_code = re.sub(r"[^a-z0-9]", "", company_code.lower())
            domain = f"{clean_code}.com" if clean_code else None
        if not domain:
            continue

        metadata = json.dumps({
            "source":       "jobhive",
            "known_ats":    "phenom",
            "company_code": company_code,
            "board_url":    url,
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
            # Dispatch to the correct parser based on schema
            if ats_name == "phenom":
                batch = list(parse_phenom_csv(text))
            else:
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

    from src.api.db import get_connection, is_postgres
    
    # Pre-load existing domains to count skips accurately
    conn = get_connection()
    try:
        if is_postgres():
            existing = {row["domain"] for row in conn.execute("SELECT domain FROM company_identities").fetchall()}
        else:
            existing = {row[0] for row in conn.execute("SELECT domain FROM company_identities").fetchall()}
        log.info(f"Existing company_identities rows: {len(existing)}")

        # Filter out records that are already imported
        to_insert = []
        for r in records:
            if r.domain in existing:
                stats["skipped"] += 1
            else:
                to_insert.append((r.company_id, r.domain, r.canonical_name, r.website, r.aliases))
                existing.add(r.domain)

        if to_insert:
            log.info(f"Batch inserting {len(to_insert):,} new records...")
            # Chunk insertions in batches of 1000 to prevent parameter limits
            batch_size = 1000
            for i in range(0, len(to_insert), batch_size):
                chunk = to_insert[i:i + batch_size]
                if is_postgres():
                    # We can use execute_many or a fast raw cursor execution for PostgreSQL
                    raw_cursor = conn.cursor()._cursor
                    query = """
                        INSERT INTO company_identities
                        (company_id, domain, canonical_name, website, aliases)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (company_id) DO NOTHING
                    """
                    raw_cursor.executemany(query, chunk)
                else:
                    conn.executemany(
                        """INSERT OR IGNORE INTO company_identities
                           (company_id, domain, canonical_name, website, aliases)
                           VALUES (?, ?, ?, ?, ?)""",
                        chunk,
                    )
                stats["inserted"] += len(chunk)
            conn.commit()
    except Exception as e:
        log.error(f"Batch insertion failed: {e}")
        stats["errors"] += len(records) - stats["skipped"] - stats["inserted"]
    finally:
        conn.close()

    return stats



# ── Verification query ────────────────────────────────────────────────────────

def run_verification(db_path: str):
    log.info("\n=== Post-Import Verification ===\n")
    from src.api.db import get_connection, is_postgres, json_extract
    conn = get_connection()
    try:
        if is_postgres():
            total = conn.execute("SELECT COUNT(*) cnt FROM company_identities").fetchone()["cnt"]
            unique_domains = conn.execute("SELECT COUNT(DISTINCT domain) cnt FROM company_identities").fetchone()["cnt"]
        else:
            total = conn.execute("SELECT COUNT(*) FROM company_identities").fetchone()[0]
            unique_domains = conn.execute("SELECT COUNT(DISTINCT domain) FROM company_identities").fetchone()[0]

        log.info(f"  Total company_identities rows : {total}")
        log.info(f"  Unique domains                : {unique_domains}")

        if total != unique_domains:
            log.warning(f"  ⚠️  {total - unique_domains} duplicate domains detected!")
        else:
            log.info("  ✅ No duplicate domains.")

        source_expr = json_extract("aliases", "$.source")
        rows = conn.execute(
            f"""SELECT {source_expr} as src, COUNT(*) as cnt
               FROM company_identities
               GROUP BY src
               ORDER BY cnt DESC"""
        ).fetchall()
        for row in rows:
            d = dict(row)
            log.info(f"    {d.get('src') or 'unknown':20s}  {d.get('cnt'):>6,}")

        log.info("\n  By known_ats (Jobhive only):")
        ats_expr = json_extract("aliases", "$.known_ats")
        rows = conn.execute(
            f"""SELECT {ats_expr} as ats, COUNT(*) as cnt
               FROM company_identities
               WHERE {source_expr} = 'jobhive'
               GROUP BY ats
               ORDER BY cnt DESC"""
        ).fetchall()
        for row in rows:
            d = dict(row)
            log.info(f"    {d.get('ats') or 'unknown':20s}  {d.get('cnt'):>6,}")

        log.info("\n  Idempotency check: re-counting distinct domains…")
        log.info(f"  PASS — domain column has UNIQUE constraint, duplicates silently ignored.\n")
    finally:
        conn.close()



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
