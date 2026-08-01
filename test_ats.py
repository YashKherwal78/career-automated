import urllib.request
import json
import ssl

darwinbox_tenants = ["adani", "swiggy", "timesinternet"]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("Testing Darwinbox...")
for t in darwinbox_tenants:
    url = f"https://{t}.darwinbox.in/ms/v3/jobs"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
            if response.status == 200:
                ct = response.headers.get("Content-Type", "")
                data = response.read().decode()
                print(f"DARWINBOX SUCCESS: {t} | CT: {ct} | snippet: {data[:150]}")
    except Exception as e:
        print(f"DARWINBOX ERROR for {t}: {e}")
