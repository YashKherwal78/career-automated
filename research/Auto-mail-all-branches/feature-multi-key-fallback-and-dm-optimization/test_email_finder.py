"""
Test suite for utils/email_finder.py and utils/scraper.enrich_recruiter_email
"""
import sys, os, logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from utils.email_finder import (
    _split_name, _extract_domain_from_url, _pick_best_email,
    extract_email_from_text, find_email_hunter, find_email_getprospect,
    find_recruiter_email, _hunter_credits_exhausted, _getprospect_credits_exhausted,
)
from utils.scraper import enrich_recruiter_email

P = "\033[92mPASS\033[0m"
F = "\033[91mFAIL\033[0m"
r = {"p": 0, "f": 0}

def check(label, ok):
    if ok: print(f"  {P} {label}"); r["p"] += 1
    else:  print(f"  {F} {label}"); r["f"] += 1

def sec(t): print(f"\n\033[94m{'─'*55}\n  {t}\n{'─'*55}\033[0m")

# ── 1. _split_name ───────────────────────────────────────────
sec("1. _split_name")
check("Two parts", _split_name("Andrea Cowan") == ("Andrea", "Cowan"))
check("Three parts", _split_name("Mary Jo Smith") == ("Mary", "Smith"))
check("Single name", _split_name("Sheryl") == ("Sheryl", ""))
check("Empty", _split_name("") == ("", ""))
check("Whitespace", _split_name("   ") == ("", ""))

# ── 2. _extract_domain_from_url ──────────────────────────────
sec("2. _extract_domain_from_url")
check("https+www", _extract_domain_from_url("https://www.meta.com") == "meta.com")
check("https no www", _extract_domain_from_url("https://stripe.com/about") == "stripe.com")
check("http", _extract_domain_from_url("http://openai.com") == "openai.com")
check("No scheme", _extract_domain_from_url("hunter.io") == "hunter.io")
check("Empty", _extract_domain_from_url("") is None)
check("None", _extract_domain_from_url(None) is None)

# ── 3. _pick_best_email ─────────────────────────────────────
sec("3. _pick_best_email")
check("Empty→None", _pick_best_email([]) is None)
check("Personal > generic", _pick_best_email(["hr@m.com", "john@m.com"]) == "john@m.com")
check("Only generic→returns it", _pick_best_email(["info@m.com"]) == "info@m.com")

# ── 4. extract_email_from_text ───────────────────────────────
sec("4. extract_email_from_text (regex)")
e, s = extract_email_from_text("Reach jane.smith@stripe.com for details.")
check("Finds plain email", e == "jane.smith@stripe.com" and s == "jd_text")
e, _ = extract_email_from_text("Send CV to john@company.com.")
check("Strips trailing period", e == "john@company.com")
e, _ = extract_email_from_text("Contact hr@acme.com or alice@acme.com")
check("Personal > hr@", e == "alice@acme.com")
e, _ = extract_email_from_text("Great opportunity!")
check("No email→None", e is None)
e, _ = extract_email_from_text("")
check("Empty→None", e is None)
e, _ = extract_email_from_text("info [at] company [dot] com")
check("Obfuscated→None", e is None)

# ── 5. Credits-exhausted detectors ───────────────────────────
sec("5. Credits-exhausted detectors")
check("Hunter 429", _hunter_credits_exhausted({"errors": [{"code": 429, "id": "usage"}]}))
check("Hunter normal→False", not _hunter_credits_exhausted({"errors": [{"code": 400, "id": "bad"}]}))
check("GP limit msg", _getprospect_credits_exhausted({"message": "limit reached"}))
check("GP normal→False", not _getprospect_credits_exhausted({"message": "ok", "status": "200"}))

# ── 6. find_email_hunter — Hunter test-api-key (live) ────────
sec("6. find_email_hunter (live test-api-key)")
try:
    email, src = find_email_hunter("Dustin Moskovitz", "asana.com", "test-api-key")
    check("Returns tuple", src == "hunter")
    check("Email is str|None", email is None or isinstance(email, str))
    print(f"    → Hunter returned: {email}")
except Exception as exc:
    check(f"No exception (got {exc})", False)

# ── 7. find_email_hunter — mocked exhausted ──────────────────
sec("7. find_email_hunter — mocked exhausted")
m = MagicMock(); m.ok = False
m.json.return_value = {"errors": [{"code": 429, "id": "usage_limit"}]}
with patch("utils.email_finder.requests.get", return_value=m):
    try:
        find_email_hunter("John Doe", "apple.com", "fake")
        check("Should raise", False)
    except RuntimeError as e:
        check("Raises credits_exhausted", "credits_exhausted" in str(e))

# ── 8. find_email_hunter — mocked success ────────────────────
sec("8. find_email_hunter — mocked success")
m = MagicMock(); m.ok = True
m.json.return_value = {"data": {"email": "Elon@Tesla.com", "score": 92}}
with patch("utils.email_finder.requests.get", return_value=m):
    e, s = find_email_hunter("Elon Musk", "tesla.com", "fake")
    check("Returns email", e == "elon@tesla.com")
    check("Source hunter", s == "hunter")

# Low score
m2 = MagicMock(); m2.ok = True
m2.json.return_value = {"data": {"email": "guess@co.com", "score": 30}}
with patch("utils.email_finder.requests.get", return_value=m2):
    e, _ = find_email_hunter("Jane", "co.com", "fake")
    check("Low score→None", e is None)

# ── 9. find_email_getprospect — mocked ───────────────────────
sec("9. find_email_getprospect — mocked")
m = MagicMock(); m.ok = True; m.status_code = 200
m.json.return_value = {"email": "R@Acme.com", "emailStatus": "verified"}
with patch("utils.email_finder.requests.post", return_value=m):
    e, s = find_email_getprospect("Rec Name", "acme.com", "gp-key")
    check("Verified email", e == "r@acme.com" and s == "getprospect")

m2 = MagicMock(); m2.ok = True; m2.status_code = 200
m2.json.return_value = {"email": "x@co.com", "emailStatus": "risky"}
with patch("utils.email_finder.requests.post", return_value=m2):
    e, _ = find_email_getprospect("Jane", "co.com", "gp-key")
    check("Risky→None", e is None)

m3 = MagicMock(); m3.ok = False; m3.status_code = 402
m3.json.return_value = {"message": "credits limit reached"}
with patch("utils.email_finder.requests.post", return_value=m3):
    try:
        find_email_getprospect("Jane", "co.com", "gp-key")
        check("Should raise", False)
    except RuntimeError as e:
        check("GP credits_exhausted", "credits_exhausted" in str(e))

# ── 10. find_recruiter_email — full cascade ──────────────────
sec("10. Full cascade")

# A: JD email short-circuits
with patch("utils.email_finder.find_email_hunter") as mh, \
     patch("utils.email_finder.find_email_getprospect") as mg:
    e, s = find_recruiter_email(jd_text="Apply jane@startup.com", hunter_api_key="k", getprospect_api_key="k")
    check("A: JD email found", e == "jane@startup.com" and s == "jd_text")
    check("A: APIs not called", mh.call_count == 0 and mg.call_count == 0)

# B: No JD email, Hunter succeeds
with patch("utils.email_finder.find_email_hunter", return_value=("f@h.com", "hunter")), \
     patch("utils.email_finder.find_email_getprospect") as mg:
    e, s = find_recruiter_email(jd_text="no email", recruiter_name="J S", company_website="https://h.com", hunter_api_key="k")
    check("B: Hunter result", e == "f@h.com" and s == "hunter")
    check("B: GP not called", mg.call_count == 0)

# C: Hunter exhausted → GP succeeds
with patch("utils.email_finder.find_email_hunter", side_effect=RuntimeError("credits_exhausted")), \
     patch("utils.email_finder.find_email_getprospect", return_value=("f@gp.com", "getprospect")):
    e, s = find_recruiter_email(jd_text="", recruiter_name="J D", company_website="https://a.com",
                                 hunter_api_key="k", getprospect_api_key="gk")
    check("C: Fallback to GP", e == "f@gp.com" and s == "getprospect")

# D: Both exhausted
with patch("utils.email_finder.find_email_hunter", side_effect=RuntimeError("credits_exhausted")), \
     patch("utils.email_finder.find_email_getprospect", side_effect=RuntimeError("credits_exhausted")):
    e, s = find_recruiter_email(jd_text="", recruiter_name="J D", company_website="https://a.com",
                                 hunter_api_key="k", getprospect_api_key="gk")
    check("D: Both exhausted→not_found", e is None and s == "not_found")

# E: No recruiter name → skip
with patch("utils.email_finder.find_email_hunter") as mh:
    e, s = find_recruiter_email(jd_text="", recruiter_name="", company_website="https://a.com", hunter_api_key="k")
    check("E: No name→skip", mh.call_count == 0 and s == "not_found")

# F: No API keys
e, s = find_recruiter_email(jd_text="", recruiter_name="A B", company_domain="a.com")
check("F: No keys→not_found", s == "not_found")

# ── 11. enrich_recruiter_email wrapper ───────────────────────
sec("11. enrich_recruiter_email wrapper")

e, s = enrich_recruiter_email({"recruiter_email": "pre@co.com", "recruiter_name": "B", "job_description": "", "company_website": ""})
check("Pre-existing email", e == "pre@co.com" and s == "jd_text")

e, s = enrich_recruiter_email({"recruiter_email": None, "recruiter_name": "J", "job_description": "Contact j@a.io", "company_website": ""})
check("JD desc email", e == "j@a.io" and s == "jd_text")

e, s = enrich_recruiter_email({"recruiter_email": None, "recruiter_name": "S", "job_description": "Great", "company_website": ""},
                               additional_context="Email: sam@big.com")
check("Additional context email", e == "sam@big.com")

with patch("utils.email_finder.find_email_hunter", return_value=("m@m.com", "hunter")):
    e, s = enrich_recruiter_email({"recruiter_email": None, "recruiter_name": "Mark Z", "job_description": "Build", "company_website": "https://meta.com"},
                                   hunter_api_key="k")
    check("Hunter enrichment via wrapper", e == "m@m.com" and s == "hunter")

# ── Summary ──────────────────────────────────────────────────
t = r["p"] + r["f"]
print(f"\n{'═'*55}")
if r["f"]: print(f"  {r['p']}/{t} passed — \033[91m{r['f']} FAILED\033[0m")
else:       print(f"  {r['p']}/{t} passed ✅ \033[92mAll tests passed!\033[0m")
print(f"{'═'*55}\n")
sys.exit(0 if r["f"] == 0 else 1)
