import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://awfis.keka.com/careers/api/jobs"
data = json.dumps({}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json", "Accept": "application/json"})

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        print(f"Status: {response.status}")
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")
