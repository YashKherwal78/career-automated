import json
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        print("Navigating to Keka careers page...")
        page.goto("https://awfis.keka.com/careers", wait_until="networkidle")
        print("Page loaded.")
        
        # Save HTML
        html = page.content()
        with open("keka_debug.html", "w") as f:
            f.write(html)
        print(f"Saved HTML. Length: {len(html)}")
        
        # Take screenshot
        page.screenshot(path="keka_debug.png")
        print("Saved screenshot.")
        
    except Exception as e:
        print(f"Error navigating: {e}")
        
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
