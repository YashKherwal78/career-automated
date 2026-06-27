import sqlite3
from src.crm.database import get_connection

# Seed Data representing the 7 categories requested by the user for the bootstrap validation
SEED_DATA = [
    # Tier 1 - AI Labs
    ("OpenAI", "openai", "greenhouse", "openai"),
    ("Anthropic", "anthropic", "greenhouse", "anthropic"),
    ("Perplexity", "perplexity", "lever", "perplexity"),
    ("Mistral AI", "mistral", "lever", "mistral"),
    ("Cohere", "cohere", "lever", "cohere"),
    ("Glean", "glean", "greenhouse", "glean"),
    ("ElevenLabs", "elevenlabs", "lever", "elevenlabs"),
    ("Runway", "runway", "greenhouse", "runway"),
    ("Character.AI", "characterai", "greenhouse", "characterai"),
    
    # Tier 2 - Developer Tools
    ("Figma", "figma", "greenhouse", "figma"),
    ("Notion", "notion", "greenhouse", "notion"),
    ("Linear", "linear", "greenhouse", "linear"),
    ("Vercel", "vercel", "greenhouse", "vercel"),
    ("Supabase", "supabase", "greenhouse", "supabase"),
    ("PostHog", "posthog", "lever", "posthog"),
    ("Retool", "retool", "lever", "retool"),
    
    # Tier 3 - Fintech
    ("Stripe", "stripe", "greenhouse", "stripe"),
    ("Brex", "brex", "greenhouse", "brex"),
    ("Mercury", "mercury", "greenhouse", "mercury"),
    ("Ramp", "ramp", "greenhouse", "ramp"),
    
    # Tier 4 - Indian Startups
    ("Razorpay", "razorpay", "greenhouse", "razorpay"),
    ("CRED", "cred", "greenhouse", "cred"),
    ("Groww", "groww", "lever", "groww"),
    ("PhonePe", "phonepe", "greenhouse", "phonepe"),
    ("Zepto", "zepto", "lever", "zepto"),
    ("Zomato", "zomato", "greenhouse", "zomato"),
    
    # Tier 5 - SaaS
    ("Atlassian", "atlassian", "lever", "atlassian"),
    ("Canva", "canva", "greenhouse", "canva"),
    ("Datadog", "datadog", "greenhouse", "datadog"),
    
    # Tier 6 - YC/VC Backed
    ("Airbnb", "airbnb", "greenhouse", "airbnb"),
    ("DoorDash", "doordash", "greenhouse", "doordash")
]

# We will synthesize 100 more companies to hit a decent validation scale
def generate_synthetic_startups():
    startups = []
    for i in range(1, 101):
        startups.append((f"YC Startup {i}", f"ycstartup{i}", "greenhouse", f"ycstartup{i}"))
    return startups

def seed_database():
    conn = get_connection()
    c = conn.cursor()
    
    all_seeds = SEED_DATA + generate_synthetic_startups()
    
    count = 0
    for company_name, slug, ats, ats_slug in all_seeds:
        gh_slug = ats_slug if ats == "greenhouse" else None
        lever_slug = ats_slug if ats == "lever" else None
        
        try:
            # Insert into static
            c.execute('''
                INSERT OR IGNORE INTO company_intelligence_static 
                (company_name, website, ats_provider, greenhouse_slug, lever_slug)
                VALUES (?, ?, ?, ?, ?)
            ''', (company_name, f"https://{slug}.com", ats, gh_slug, lever_slug))
            
            # Insert into dynamic
            c.execute('''
                INSERT OR IGNORE INTO hiring_intelligence_dynamic 
                (company_name) VALUES (?)
            ''', (company_name,))
            count += 1
        except Exception as e:
            print(f"Failed to seed {company_name}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Successfully seeded {count} companies into Company Intelligence Database.")

if __name__ == "__main__":
    seed_database()
