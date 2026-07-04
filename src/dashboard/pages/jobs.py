import streamlit as st
import pandas as pd
from src.dashboard.services.database import fetch_query
import json

st.title("Opportunity Dashboard")
st.markdown("All discovered opportunities, intelligently ranked.")

# Fetch the 'normalized_jobs' table with company names
jobs_df = fetch_query("SELECT j.*, c.canonical_name as company_name FROM normalized_jobs j LEFT JOIN company_identities c ON j.company_id = c.company_id")

if jobs_df.empty:
    st.info("No opportunities discovered yet.")
else:
    # --- Sorting Controls ---
    st.sidebar.header("Sort Options")
    sort_by = st.sidebar.selectbox(
        "Sort By", 
        ["Queue Rank", "Final Score", "Confidence", "Freshness", "Company"]
    )
    
    # Map selection to columns
    sort_col_map = {
        "Queue Rank": "job_score",
        "Final Score": "job_score",
        "Confidence": "scoring_confidence",
        "Freshness": "posted_at",
        "Company": "company_id"
    }
    
    ascending = True
    if sort_by in ["Final Score", "Confidence", "Freshness"]:
        ascending = False
        
    jobs_df = jobs_df.sort_values(by=sort_col_map[sort_by], ascending=ascending)
    
    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    pipeline_filter = st.sidebar.multiselect("Pipeline", jobs_df['provider'].unique() if 'provider' in jobs_df.columns else ["OFFICIAL", "MARKET"])
    connector_filter = st.sidebar.multiselect("Provider", jobs_df['provider'].unique() if 'provider' in jobs_df.columns else [])
    company_filter = st.sidebar.multiselect("Company", sorted(jobs_df['company_name'].dropna().unique()))
    recommendation_filter = st.sidebar.multiselect("Recommendation", jobs_df['recommendation_reason'].unique() if 'recommendation_reason' in jobs_df.columns else [])
    
    filtered_df = jobs_df.copy()
    if pipeline_filter and 'provider' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['provider'].isin(pipeline_filter)]
    if connector_filter:
        filtered_df = filtered_df[filtered_df['provider'].isin(connector_filter)]
    if company_filter:
        filtered_df = filtered_df[filtered_df['company_name'].isin(company_filter)]
    if recommendation_filter and 'recommendation' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['recommendation'].isin(recommendation_filter)]
        
    st.markdown(f"**Showing {len(filtered_df)} Opportunities**")
    
    # --- Tabs Setup ---
    tab1, tab2, tab3 = st.tabs(["⭐ Priority Queue", "🏢 Official Opportunities", "🌍 Market Opportunities"])
    
    def render_job_card(row):
        score = row.get('job_score', 0)
        role = row.get('title', 'Unknown')
        company = row.get('company_name', 'Unknown')
        recommendation = "Recommended" if score > 50 else "UNKNOWN"
        rank = row.get('job_score', 0)
        confidence = row.get('scoring_confidence', 0.0)
        if pd.isna(confidence) or confidence is None:
            confidence = 0.0
        provider = row.get('provider', 'Unknown')
        pipeline = "MARKET" if provider in ['LinkedIn', 'Wellfound'] else "OFFICIAL"
        source_platform = provider
        connector = provider
        freshness = row.get('posted_at', 'Unknown')
        
        badge = "🏢 Official ATS" if pipeline == "OFFICIAL" else "🌍 Market"
        
        with st.expander(f"[{recommendation}] #{rank} - {role} @ {company} (Score: {score})"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Company**: {company}")
                st.markdown(f"**Role**: {role}")
                st.markdown(f"**Location**: {row.get('location', 'Unknown')}")
                st.markdown(f"**Source**: {badge} • {source_platform}")
            with c2:
                st.markdown(f"**Recommendation**: {recommendation}")
                st.markdown(f"**Final Score**: {score}")
                st.markdown(f"**Confidence**: {confidence*100:.0f}%")
                st.markdown(f"**Freshness**: {freshness}")
                
                button_text = f"Apply on {source_platform}" if pipeline == "MARKET" else "Apply on Company Website"
                st.markdown(f"**Action**: [{button_text}]({row.get('apply_url', '#')})")
                
            # JIE Qualification Chips
            st.markdown("---")
            st.markdown("### Job Qualifications (JIE)")
            chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
            
            exp_min = row.get("experience_min")
            exp_max = row.get("experience_max")
            if pd.isna(exp_min): exp_min = None
            if pd.isna(exp_max): exp_max = None
            exp_str = "Unknown"
            if exp_min is not None and exp_max is not None:
                exp_str = f"{int(exp_min)}-{int(exp_max)} Years"
            elif exp_min is not None:
                exp_str = f"{int(exp_min)}+ Years"
                
            work_mode = row.get("work_mode", "Unknown")
            employment = row.get("employment_type", "Unknown")
            domain = row.get("domain", "Unknown")
            
            with chip_col1: st.info(f"💼 **Exp**: {exp_str}")
            with chip_col2: st.info(f"📍 **Mode**: {work_mode}")
            with chip_col3: st.info(f"⏳ **Type**: {employment}")
            with chip_col4: st.info(f"🏢 **Domain**: {domain}")
            
            jie_payload_str = row.get('jie_payload')
            if pd.notna(jie_payload_str) and jie_payload_str:
                try:
                    jie_data = json.loads(jie_payload_str)
                    reqs = jie_data.get("requirements", [])
                    mandatory = [r['name'] for r in reqs if r.get('importance') == 'REQUIRED' and r.get('type') == 'skill']
                    preferred = [r['name'] for r in reqs if r.get('importance') == 'PREFERRED' and r.get('type') == 'skill']
                    
                    if mandatory:
                        st.markdown("**Required Skills**: `" + "` `".join(mandatory) + "`")
                    if preferred:
                        st.markdown("**Preferred Skills**: `" + "` `".join(preferred) + "`")
                except Exception as e:
                    pass
            
            st.markdown("---")
            st.markdown("**Explainability Receipt (Why am I seeing this?)**")
            
            notes = row.get('ranking_reason', '{}')
            try:
                receipt = json.loads(notes)
                if isinstance(receipt, dict):
                    md_receipt = ""
                    for k, v in receipt.items():
                        md_receipt += f"- **{k}**: {v}\n"
                    st.markdown(md_receipt)
                else:
                    st.markdown(f"**Notes**: {', '.join(receipt)}")
            except:
                st.markdown(f"**Notes**: {notes}")
                
            st.markdown("---")
            desc = str(row.get('description', ''))
            st.markdown(f"**Description Snippet**: {desc[:500]}...")

    with tab1:
        st.subheader("Today's Unified Application Queue")
        for _, row in filtered_df.iterrows():
            render_job_card(row)
            
    with tab2:
        st.subheader("Official Pipeline (ATS)")
        official_df = filtered_df[~filtered_df['provider'].isin(['LinkedIn', 'Wellfound'])] if 'provider' in filtered_df.columns else pd.DataFrame()
        if official_df.empty:
            st.info("No official opportunities found matching criteria.")
        else:
            connectors = official_df['provider'].unique() if 'provider' in official_df.columns else ["Greenhouse"]
            for conn in connectors:
                st.markdown(f"### 🏢 {str(conn).capitalize()} Jobs")
                conn_df = official_df[official_df['provider'] == conn] if 'provider' in official_df.columns else official_df
                for _, row in conn_df.iterrows():
                    render_job_card(row)
            
    with tab3:
        st.subheader("Market Discovery Pipeline")
        market_df = filtered_df[filtered_df['provider'].isin(['LinkedIn', 'Wellfound'])] if 'provider' in filtered_df.columns else filtered_df
        if market_df.empty:
            st.info("No market opportunities found matching criteria.")
        else:
            # Group by connector
            connectors = market_df['provider'].unique() if 'provider' in market_df.columns else ["LinkedIn"]
            for conn in connectors:
                st.markdown(f"### 🔗 {str(conn).capitalize()} Jobs")
                conn_df = market_df[market_df['provider'] == conn] if 'provider' in market_df.columns else market_df
                for _, row in conn_df.iterrows():
                    render_job_card(row)
