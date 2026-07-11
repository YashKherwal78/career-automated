import streamlit as st
import pandas as pd
from datetime import datetime
from src.dashboard.services.database import fetch_table

st.title("Outreach Engine")

jobs_df = fetch_table("discovered_jobs")

if jobs_df.empty:
    st.info("No outreach data available.")
else:
    outreach_df = jobs_df[jobs_df['outreach_scheduled_for'].notnull()]
    
    scheduled = len(outreach_df[outreach_df['status'] == 'APPLIED'])
    sent = len(outreach_df[outreach_df['status'] == 'OUTREACH_SENT'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Scheduled Emails", scheduled)
    with col2:
        st.metric("Sent Emails", sent)
    with col3:
        st.metric("Failed Emails", 0) # Tracked separately or derived
    with col4:
        st.metric("Delivery Failures", 0)
        
    st.divider()
    
    st.subheader("Recent & Pending Emails")
    for _, row in outreach_df.sort_values(by='outreach_scheduled_for', ascending=False).iterrows():
        state_color = "🟢" if row['status'] == "OUTREACH_SENT" else "🟡"
        with st.expander(f"{state_color} {row['company']} - {row['role']}"):
            st.markdown(f"**Scheduled For**: {row['outreach_scheduled_for']}")
            if row['status'] == 'OUTREACH_SENT':
                st.markdown(f"**Sent At**: {row['updated_at']}")
            st.markdown(f"**Status**: {row['status']}")
