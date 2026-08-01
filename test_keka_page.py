import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://msystechnologies.keka.com/careers"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        print(f"Status: {response.status}")
        print("Headers:", response.headers)
        html = response.read().decode()
        print("HTML Snippet:", html[:500])
except Exception as e:
    print(f"Error: {e}")

url = "https://awfis.keka.com/careers"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        print(f"Status: {response.status}")
        html = response.read().decode()
        print("HTML Snippet:", html[:500])
except Exception as e:
    print(f"Error: {e}")
