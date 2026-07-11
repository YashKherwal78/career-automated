import streamlit as st
import sqlite3
import pandas as pd
from src.config.config import Config
import json

st.set_page_config(page_title="Application History", layout="wide")
st.title("Application History")

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()

# Metrics
c = conn.cursor()
c.execute("SELECT status, count(*) as count FROM application_executions GROUP BY status")
status_counts = {row["status"]: row["count"] for row in c.fetchall()}

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Submitted", status_counts.get("SUBMITTED", 0))
col2.metric("Failed", status_counts.get("FAILED", 0))
col3.metric("Review Required", status_counts.get("REVIEW_REQUIRED", 0))
col4.metric("Skipped", status_counts.get("SKIPPED", 0))

st.markdown("---")

# Filters
status_filter = st.selectbox("Filter by Status", ["ALL", "SUBMITTED", "FAILED", "REVIEW_REQUIRED", "SKIPPED", "READY", "IN_PROGRESS"])

query = """
    SELECT ae.*, j.ranking_score 
    FROM application_executions ae
    JOIN jobs j ON ae.job_id = j.id
"""
if status_filter != "ALL":
    query += f" WHERE ae.status = '{status_filter}'"
query += " ORDER BY ae.updated_at DESC LIMIT 100"

df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    st.info("No application history found matching the filters.")
else:
    for index, row in df.iterrows():
        with st.expander(f"{row['company']} - {row['job_title']} ({row['status']}) - {row['updated_at']}"):
            st.markdown(f"**Connector**: {row['connector']}")
            st.markdown(f"**Apply URL**: {row['apply_url']}")
            st.markdown(f"**Resume Used**: {row['resume_variant']} ({row['tailored_resume_path']})")
            
            if row['status'] == "SUBMITTED":
                st.success(f"Successfully submitted! Confirmation URL: {row['confirmation_url']}")
            elif row['status'] == "FAILED" or row['status'] == "REVIEW_REQUIRED":
                st.error(f"Failure Reason: {row['failure_reason']}")
                
            if row['submitted_answers']:
                st.markdown("### Submitted Answers")
                answers = json.loads(row['submitted_answers'])
                st.json(answers)
                
            if row['screenshot_path']:
                try:
                    st.image(row['screenshot_path'], caption="Final State Screenshot")
                except:
                    st.warning("Screenshot not available.")
