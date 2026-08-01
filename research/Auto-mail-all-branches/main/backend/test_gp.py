import requests

for ep in ["email-finder/search", "emails", "leads", "contacts", "v2/email", "v1/search"]:
    resp = requests.post(f"https://api.getprospect.com/public/v1/{ep}", json={})
    print(ep, resp.status_code, resp.text)
    
