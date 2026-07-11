import streamlit as st
import pandas as pd
from src.dashboard.services.database import fetch_table

st.title("Execution Queue")

jobs_df = fetch_table("discovered_jobs")

if jobs_df.empty:
    st.info("No jobs in queue.")
else:
    # Get counts for the linear queue
    discovered = len(jobs_df[jobs_df['status'] == 'DISCOVERED'])
    matched = len(jobs_df[jobs_df['status'] == 'MATCHED'])
    applied = len(jobs_df[jobs_df['status'] == 'APPLIED'])
    outreach_sent = len(jobs_df[jobs_df['status'] == 'OUTREACH_SENT'])
    
    st.markdown("### The Pipeline")
    
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 2, 1, 2, 1, 2])
    
    with col1:
        st.markdown("<div style='text-align:center; padding: 20px; border:1px solid #1f77b4; border-radius:10px;'><h3>DISCOVERED</h3><h1>{}</h1></div>".format(discovered), unsafe_allow_html=True)
    with col2:
        st.markdown("<h2 style='text-align:center; margin-top:30px;'>➔</h2>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div style='text-align:center; padding: 20px; border:1px solid #1f77b4; border-radius:10px;'><h3>MATCHED</h3><h1>{}</h1></div>".format(matched), unsafe_allow_html=True)
    with col4:
        st.markdown("<h2 style='text-align:center; margin-top:30px;'>➔</h2>", unsafe_allow_html=True)
    with col5:
        st.markdown("<div style='text-align:center; padding: 20px; border:1px solid #1f77b4; border-radius:10px;'><h3>APPLIED</h3><h1>{}</h1></div>".format(applied), unsafe_allow_html=True)
    with col6:
        st.markdown("<h2 style='text-align:center; margin-top:30px;'>➔</h2>", unsafe_allow_html=True)
    with col7:
        st.markdown("<div style='text-align:center; padding: 20px; border:1px solid #1f77b4; border-radius:10px;'><h3>OUTREACH</h3><h1>{}</h1></div>".format(outreach_sent), unsafe_allow_html=True)

    st.divider()
    
    st.markdown("### Queue Backlog Warnings")
    if discovered > 100:
        st.warning(f"**Discovery Backlog**: {discovered} jobs waiting to be scored by Match Engine.")
    if matched > 50:
        st.warning(f"**Application Backlog**: {matched} matched jobs waiting for Application Worker.")
    if applied > 20:
        st.info(f"**Outreach Pending**: {applied} applications awaiting outreach delay.")
        
    if discovered <= 100 and matched <= 50 and applied <= 20:
        st.success("Queue is healthy and flowing optimally.")
