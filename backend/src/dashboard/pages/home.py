import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
from src.config.config import Config

st.title("Mission Control (True North KPI)")

def fetch_df(query):
    conn = sqlite3.connect(Config.DATABASE_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Fetch core data
registry_df = fetch_df("SELECT c.canonical_name as company_name, c.domain, e.ats_provider FROM company_identities c LEFT JOIN career_endpoints e ON c.company_id = e.company_id")
jobs_df = fetch_df("SELECT j.*, c.canonical_name as company_name FROM normalized_jobs j JOIN company_identities c ON j.company_id = c.company_id")

# --- Registry Metrics ---
total_companies = len(registry_df)

companies_with_jobs = jobs_df['company_name'].nunique() if not jobs_df.empty else 0
coverage_pct = int((companies_with_jobs / total_companies) * 100) if total_companies else 0

unknown_ats = len(registry_df[registry_df['ats_provider'].isnull() | (registry_df['ats_provider'].str.lower() == 'unknown')]) if not registry_df.empty else 0

# --- Outcome Metrics ---
today_str = date.today().isoformat()
jobs_found_today = 0
if 'posting_date' in jobs_df.columns and 'created_at' in jobs_df.columns:
    jobs_found_today = len(jobs_df[jobs_df['posting_date'].str.startswith(today_str, na=False) | jobs_df['created_at'].str.startswith(today_str, na=False)])
elif 'created_at' in jobs_df.columns:
    jobs_found_today = len(jobs_df[jobs_df['created_at'].str.startswith(today_str, na=False)])

relevant_jobs = jobs_df[jobs_df['ranking_score'] >= 100] if 'ranking_score' in jobs_df.columns else pd.DataFrame()
relevant_pm = len(relevant_jobs[relevant_jobs['recommended_resume'] == 'Product']) if 'recommended_resume' in relevant_jobs.columns else 0
relevant_ai = len(relevant_jobs[relevant_jobs['recommended_resume'] == 'AI/Data']) if 'recommended_resume' in relevant_jobs.columns else 0
relevant_swe = len(relevant_jobs[relevant_jobs['recommended_resume'] == 'Engineering']) if 'recommended_resume' in relevant_jobs.columns else 0
relevant_founder = len(relevant_jobs[relevant_jobs['recommended_resume'] == 'Strategy']) if 'recommended_resume' in relevant_jobs.columns else 0

applications_sent = 0
if 'status' in jobs_df.columns and 'updated_at' in jobs_df.columns:
    applications_sent = len(jobs_df[(jobs_df['status'] == 'APPLIED') & (jobs_df['updated_at'].str.startswith(today_str, na=False))])
interviews = len(jobs_df[jobs_df['status'] == 'INTERVIEW'])
replies = len(jobs_df[jobs_df['status'].isin(['INTERVIEW', 'OFFER', 'REJECTED'])])

# --- Display Registry Coverage ---
st.subheader("Discovery Coverage (Registry)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Companies Found", total_companies)
    st.metric("Companies w/ Verified ATS", len(registry_df[registry_df['ats_provider'].notnull()]))
with c2:
    st.metric("Companies Producing Jobs", companies_with_jobs)
with c3:
    st.metric("Total Coverage", f"{coverage_pct}%")
with c4:
    st.metric("Unknown ATS", unknown_ats)
    
st.divider()

# --- Display Outcome Metrics ---
st.subheader("The Only Metrics That Matter (Today)")
o1, o2, o3, o4 = st.columns(4)
with o1:
    st.metric("Jobs Found Today", jobs_found_today)
    st.metric("Applications Sent", applications_sent)
with o2:
    st.metric("Relevant PM", relevant_pm)
    st.metric("Interviews", interviews)
with o3:
    st.metric("Relevant AI", relevant_ai)
    st.metric("Replies", replies)
with o4:
    st.metric("Relevant SWE", relevant_swe)
    st.metric("Relevant Strategy", relevant_founder)

st.divider()

st.info("The primary goal is increasing Applications Sent week over week.")
