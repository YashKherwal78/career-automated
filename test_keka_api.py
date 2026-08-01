import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    "https://awfis.keka.com/careers/api/jobs",
    "https://awfis.keka.com/careers/api/job",
    "https://awfis.keka.com/careers/api/jobProfile",
    "https://awfis.keka.com/careers/api/jobPosting",
    "https://awfis.keka.com/careers/api/v1/jobs",
    "https://awfis.keka.com/keka-api/careers/jobs"
]

for url in urls:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            print(f"SUCCESS: {url} - Status: {response.status}")
    except Exception as e:
        print(f"FAILED: {url} - Error: {e}")
