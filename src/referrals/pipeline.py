import json
import sqlite3
from src.crm.database import DB_PATH
from src.referrals.discovery import discover_contacts
from src.referrals.profile_intelligence import scrape_profile
from src.referrals.scoring import score_contact
from src.referrals.email_discovery import discover_email

def run_referral_engine(company_name: str, job_title: str, job_description: str = ""):
    """
    Executes the V0.1 Referral Engine flow:
    1. Safe Job Discovery (Max 5 contacts)
    2. Profile Intelligence
    3. Referral Scoring
    4. Email Discovery (Top 3 only)
    5. Save to CRM
    """
    print(f"\n🚀 [Referral Engine] Initiating for {company_name} - {job_title}")
    
    # Step 1: Discovery
    contacts = discover_contacts(company_name, job_title, job_description)
    if not contacts:
        print("❌ [Referral Engine] No contacts discovered.")
        return
        
    print(f"✅ Discovered {len(contacts)} potential contacts.")
    
    # Step 2 & 3: Intelligence & Scoring
    scored_contacts = []
    for contact in contacts:
        # Get raw profile JSON
        profile_json = scrape_profile(contact["linkedin_url"])
        
        # Score the contact based on profile and role
        score, reason = score_contact(contact, profile_json, job_title)
        contact["referral_score"] = score
        contact["ranking_reason"] = reason
        contact["raw_profile_json"] = json.dumps(profile_json)
        contact["profile_confidence"] = profile_json.get("profile_confidence", 0)
        
        scored_contacts.append(contact)
        
    # Sort by score descending
    scored_contacts.sort(key=lambda x: x["referral_score"], reverse=True)
    
    # Step 4: Email Discovery (Top 3 only)
    top_3 = scored_contacts[:3]
    for contact in top_3:
        email, confidence = discover_email(contact["contact_name"], company_name)
        contact["email"] = email
        contact["email_confidence"] = confidence
        
    # Set email=None for the rest
    for contact in scored_contacts[3:]:
        contact["email"] = None
        contact["email_confidence"] = 0
        
    # Step 5: Save to CRM
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for contact in scored_contacts:
        cursor.execute('''
            INSERT OR IGNORE INTO referral_contacts 
            (company, job_title, contact_name, linkedin_url, email, email_confidence, 
             contact_type, discovery_source, profile_confidence, raw_profile_json, referral_score, ranking_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contact["company"], contact["job_title"], contact["contact_name"], contact["linkedin_url"],
            contact["email"], contact["email_confidence"], contact["contact_type"], contact["discovery_source"],
            contact["profile_confidence"], contact["raw_profile_json"], contact["referral_score"], contact["ranking_reason"]
        ))
    conn.commit()
    conn.close()
    
    print(f"✅ [Referral Engine] Successfully logged {len(scored_contacts)} contacts into the CRM.")
