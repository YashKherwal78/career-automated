import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.dashboard.services.database import get_latest_heartbeats

st.title("Worker Agents Health")

heartbeats = get_latest_heartbeats()

if heartbeats.empty:
    st.info("No worker heartbeats logged yet.")
else:
    # Expected workers
    expected = [
        "Startup Health", 
        "Discovery Worker", 
        "Match Worker", 
        "Application Worker", 
        "Outreach Worker"
    ]
    
    st.markdown("### Active Services")
    
    for worker in expected:
        worker_data = heartbeats[heartbeats['worker_name'] == worker]
        
        if worker_data.empty:
            st.warning(f"**{worker}**: No heartbeat found. Status: UNKNOWN")
            continue
            
        row = worker_data.iloc[0]
        
        # Check heartbeat freshness (e.g. within last 24 hours since it's a daily cron)
        last_run = datetime.strptime(row['finished_at'], '%Y-%m-%d %H:%M:%S')
        hours_since_run = (datetime.now() - last_run).total_seconds() / 3600
        
        if row['status'] == 'FAILED':
            status_col = "🔴 FAILED"
        elif hours_since_run > 25:
            status_col = "🟡 WARNING (Stale)"
        else:
            status_col = "🟢 HEALTHY"
            
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader(worker)
                st.markdown(f"**Status**: {status_col}")
            with col2:
                st.markdown(f"**Last Run**: {row['finished_at']}")
                st.markdown(f"**Execution Time**: {row['execution_time']:.2f}s")
            with col3:
                st.markdown(f"**Items Processed**: {row['items_processed']}")
