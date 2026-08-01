import json
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    
    urls = {
        "swiggy": "https://careers.swiggy.com/",
        "zoho": "https://zohocorp.zohorecruit.com/jobs/Careers"
    }

    for name, url in urls.items():
        print(f"\n--- Tracing {name} at {url} ---")
        api_calls = []
        def handle_response(response, nm=name):
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    if "json" in response.headers.get("content-type", ""):
                        api_calls.append(response.url)
                except:
                    pass
        
        page.on("response", handle_response)
        
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
            
            html = page.content()
            with open(f"{name}_debug.html", "w") as f:
                f.write(html)
            print(f"Saved HTML length: {len(html)}")
        except Exception as e:
            print(f"Error navigating: {e}")
            
        print("API Calls with JSON:")
        for call in set(api_calls):
            print(call)
            
        # Remove listener for next iteration
        page.remove_listener("response", handle_response)

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
