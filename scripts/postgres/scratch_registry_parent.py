import sqlite3
conn = sqlite3.connect("data/crm.db")
conn.row_factory = sqlite3.Row

# Are company_master and company_identities the same companies with different ID schemes?
cm_domains = set(r["domain"] for r in conn.execute("SELECT domain FROM company_master WHERE domain IS NOT NULL").fetchall())
ci_domains = set(r["domain"] for r in conn.execute("SELECT domain FROM company_identities WHERE domain IS NOT NULL").fetchall())
print(f"company_master non-null domains: {len(cm_domains)}")
print(f"company_identities non-null domains: {len(ci_domains)}")
print(f"Domain overlap: {len(cm_domains & ci_domains)}")
print(f"In master only: {len(cm_domains - ci_domains)}")
print(f"In identities only: {len(ci_domains - cm_domains)}")

# Total rows across all registry data tables
all_registry_tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'registry_%' AND name NOT LIKE '%_state' AND name != 'registry_history'"
).fetchall()]
total_registry_rows = sum(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in all_registry_tables)
cm_rows = conn.execute("SELECT COUNT(*) FROM company_master").fetchone()[0]
print(f"\nTotal rows across all registry data tables ({len(all_registry_tables)} tables): {total_registry_rows}")
print(f"company_master rows: {cm_rows}")
print("Match:", total_registry_rows == cm_rows)
print("-> registry_* are provider-specific partitions of company_master")

# What does company_master NOT have that company_identities does?
print("\n=== Key architectural insight ===")
print("company_master: provider-slug PKs (e.g. 'ashby_0g'), no domain (mostly NULL)")
print("company_identities: domain-hash PKs (e.g. 'ashbyhq-com-xxx'), domain is the key")
print("These are DIFFERENT entity schemes — legacy vs new")
