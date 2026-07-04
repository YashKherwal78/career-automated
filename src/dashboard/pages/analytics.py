import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.services.database import fetch_table, fetch_query

st.title("Analytics & Visualization")

jobs_df = fetch_table("discovered_jobs")

if jobs_df.empty:
    st.info("Not enough data to generate analytics.")
else:
    # Convert updated_at to datetime
    jobs_df['date'] = pd.to_datetime(jobs_df['updated_at']).dt.date
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Jobs Discovered Per Day")
        disc_counts = jobs_df.groupby('date').size().reset_index(name='count')
        fig1 = px.bar(disc_counts, x='date', y='count', color_discrete_sequence=['#1f77b4'])
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Applications Per Day")
        apps_df = jobs_df[jobs_df['status'].isin(['APPLIED', 'OUTREACH_SENT', 'INTERVIEW', 'OFFER', 'REJECTED'])]
        app_counts = apps_df.groupby('date').size().reset_index(name='count')
        fig2 = px.line(app_counts, x='date', y='count', markers=True, color_discrete_sequence=['#2ca02c'])
        st.plotly_chart(fig2, use_container_width=True)
        
    st.divider()
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Pipeline Funnel")
        # Map statuses to ordered funnel
        status_counts = jobs_df['status'].value_counts().reset_index()
        status_counts.columns = ['status', 'count']
        
        # Define funnel order
        funnel_order = ['DISCOVERED', 'MATCHED', 'APPLIED', 'OUTREACH_SENT', 'INTERVIEW', 'OFFER']
        funnel_data = pd.DataFrame({'status': funnel_order})
        funnel_data = funnel_data.merge(status_counts, on='status', how='left').fillna(0)
        
        fig3 = px.funnel(funnel_data, x='count', y='status')
        st.plotly_chart(fig3, use_container_width=True)
        
    with col4:
        st.subheader("Top Roles")
        roles = jobs_df['role'].value_counts().head(5).reset_index()
        roles.columns = ['role', 'count']
        fig4 = px.pie(roles, values='count', names='role')
        st.plotly_chart(fig4, use_container_width=True)
