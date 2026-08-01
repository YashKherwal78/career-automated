import os
from supabase import create_client, Client
import logging

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_ANON_KEY", "")  # Or service role key

supabase: Client = None
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logging.error(f"Failed to init Supabase: {e}")

def get_profile(email: str) -> dict:
    if not supabase:
        return {}
    try:
        res = supabase.table("profiles").select("*").eq("email", email).execute()
        if res.data:
            return res.data[0]
        return {}
    except Exception as e:
        logging.error(f"Supabase GET error: {e}")
        return {}

def upsert_profile(profile_data: dict) -> dict:
    if not supabase:
        return profile_data
    try:
        email = profile_data.get("email")
        if not email:
            return profile_data
        
        existing = get_profile(email)
        if existing and "id" in existing:
            profile_data["id"] = existing["id"]
            
        res = supabase.table("profiles").upsert(profile_data).execute()
        if res.data:
            return res.data[0]
        return profile_data
    except Exception as e:
        logging.error(f"Supabase UPSERT error: {e}")
        return profile_data
