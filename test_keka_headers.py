import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    "https://awfis.keka.com/careers/api/jobs",
    "https://awfis.keka.com/keka-api/careers/jobs",
    "https://awfis.keka.com/careers/api/jobs/"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://awfis.keka.com/careers/"
}

for url in urls:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            print(f"SUCCESS: {url} - Status: {response.status}")
            print(response.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print(f"FAILED: {url} - Error: HTTP {e.code}")
    except Exception as e:
        print(f"FAILED: {url} - Error: {e}")
