from src.crm.database import get_connection

AI_COMPANIES = [
    ("OpenAI", "openai", "greenhouse", "openai"),
    ("Anthropic", "anthropic", "greenhouse", "anthropic"),
    ("Perplexity", "perplexity", "lever", "perplexity"),
    ("Mistral AI", "mistral", "lever", "mistral"),
    ("Cohere", "cohere", "lever", "cohere"),
    ("Glean", "glean", "greenhouse", "glean"),
    ("ElevenLabs", "elevenlabs", "lever", "elevenlabs"),
    ("Runway", "runway", "greenhouse", "runway"),
    ("Character.AI", "characterai", "greenhouse", "characterai")
]

def import_ai_companies():
    conn = get_connection()
    c = conn.cursor()
    count = 0
    for company_name, slug, ats, ats_slug in AI_COMPANIES:
        gh_slug = ats_slug if ats == "greenhouse" else None
        lever_slug = ats_slug if ats == "lever" else None
        
        try:
            c.execute('''
                INSERT OR IGNORE INTO company_intelligence_static 
                (company_name, website, ats_provider, greenhouse_slug, lever_slug, industry)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (company_name, f"https://{slug}.com", ats, gh_slug, lever_slug, "AI"))
            
            c.execute('''
                INSERT OR IGNORE INTO hiring_intelligence_dynamic 
                (company_name) VALUES (?)
            ''', (company_name,))
            count += 1
        except Exception as e:
            print(f"Failed to seed {company_name}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} AI companies.")
    
if __name__ == "__main__":
    import_ai_companies()
