#!/usr/bin/env python3
"""
Update GoDaddy DNS records for a domain.

Usage:
  export GODADDY_KEY=your_key
  export GODADDY_SECRET=your_secret
  python3 scripts/godaddy_update.py careerautomated.in

This script requires the environment variables `GODADDY_KEY` and
`GODADDY_SECRET`. It will add/update the following records for
`careerautomated.in`:
  - A @ -> 76.76.21.21
  - CNAME www -> cname.vercel-dns.com
  - CNAME api -> v0t9rz3o.up.railway.app
  - TXT _railway-verify.api -> railway-verify=...

Be careful: running this will overwrite the specified records on the
domain. The script prints the HTTP response for each call.
"""
import os
import sys
import json
import requests

GODADDY_API = "https://api.godaddy.com/v1"


def auth_headers():
    key = os.environ.get("GODADDY_KEY")
    secret = os.environ.get("GODADDY_SECRET")
    if not key or not secret:
        print("ERROR: Set GODADDY_KEY and GODADDY_SECRET in environment.")
        sys.exit(1)
    return {"Authorization": f"sso-key {key}:{secret}", "Content-Type": "application/json"}


def put_record(domain, rtype, name, records):
    url = f"{GODADDY_API}/domains/{domain}/records/{rtype}/{name}"
    resp = requests.put(url, headers=auth_headers(), data=json.dumps(records))
    print(f"PUT {rtype} {name} -> {domain} -> status {resp.status_code}")
    try:
        print(resp.text)
    except Exception:
        pass
    if resp.status_code >= 400:
        print("Error updating record, aborting.")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/godaddy_update.py domain.com")
        sys.exit(1)
    domain = sys.argv[1].strip()

    # Records to apply
    records = [
        ("A", "@", [{"data": "76.76.21.21", "ttl": 600}]),
        ("CNAME", "www", [{"data": "cname.vercel-dns.com", "ttl": 3600}]),
        ("A", "api", [{"data": "34.131.238.232", "ttl": 3600}])
    ]

    print(f"Updating DNS for {domain} using GoDaddy API")
    for rtype, name, body in records:
        print(f"Applying {rtype} {name} -> {body}")
        put_record(domain, rtype, name, body)

    print("Done. Allow DNS propagation a few minutes to an hour.")


if __name__ == '__main__':
    main()
