from src.crm.database import get_connection

INDIAN_STARTUPS = [
    ("Swiggy", "swiggy", "greenhouse", "swiggy", True),
    ("Paytm", "paytm", "lever", "paytm", True),
    ("Unacademy", "unacademy", "greenhouse", "unacademy", True),
    ("Postman", "postman", "lever", "postman", True),
    ("BrowserStack", "browserstack", "greenhouse", "browserstack", True),
    ("Ola", "ola", "greenhouse", "ola", True),
    ("CureFit", "curefit", "lever", "curefit", True),
    ("Meesho", "meesho", "greenhouse", "meesho", True),
    ("ShareChat", "sharechat", "lever", "sharechat", True),
    ("Lenskart", "lenskart", "greenhouse", "lenskart", True),
    ("Upstox", "upstox", "lever", "upstox", True),
    ("CRED", "cred", "greenhouse", "cred", True),
    ("Groww", "groww", "lever", "groww", True),
    ("PhonePe", "phonepe", "greenhouse", "phonepe", True),
    ("Zepto", "zepto", "lever", "zepto", True),
    ("Zomato", "zomato", "greenhouse", "zomato", True),
    ("Razorpay", "razorpay", "greenhouse", "razorpay", True)
]

def import_indian_startups():
    conn = get_connection()
    c = conn.cursor()
    count = 0
    for company_name, slug, ats, ats_slug, hiring_in_india in INDIAN_STARTUPS:
        gh_slug = ats_slug if ats == "greenhouse" else None
        lever_slug = ats_slug if ats == "lever" else None
        
        try:
            c.execute('''
                INSERT OR IGNORE INTO company_intelligence_static 
                (company_name, website, ats_provider, greenhouse_slug, lever_slug, hiring_in_india)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (company_name, f"https://{slug}.com", ats, gh_slug, lever_slug, hiring_in_india))
            
            c.execute('''
                INSERT OR IGNORE INTO hiring_intelligence_dynamic 
                (company_name) VALUES (?)
            ''', (company_name,))
            count += 1
        except Exception as e:
            print(f"Failed to seed {company_name}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} Indian startups.")
    
if __name__ == "__main__":
    import_indian_startups()
