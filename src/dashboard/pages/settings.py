import streamlit as st
import os
from src.config.config import Config

st.title("System Configuration")

st.markdown("This control center provides a read-only view of the active `config.py` environment.")

st.subheader("Global Limits")
st.markdown(f"**Applications Per Day**: {getattr(Config, 'WELLFOUND_DAILY_LIMIT', 3)}")
st.markdown(f"**Opportunity Score Threshold**: 75")
st.markdown(f"**Outreach Delay**: 2-6 Hours")

st.divider()

st.subheader("Subsystem Status")

groq_status = "🟢 ACTIVE" if os.getenv("GROQ_API_KEY") else "🔴 OFFLINE"
apify_status = "🟢 ACTIVE" if Config.APIFY_KEYS or os.getenv("APIFY_API_KEY") else "🔴 OFFLINE"
smtp_status = "🟢 ACTIVE" if os.getenv("SMTP_USER") and os.getenv("SMTP_APP_PASSWORD") else "🔴 OFFLINE"

st.markdown(f"**Groq Inference Engine**: {groq_status}")
st.markdown(f"**Apify Discovery**: {apify_status}")
st.markdown(f"**SMTP Email Relay**: {smtp_status}")

st.divider()

st.subheader("Strategies")
st.markdown("**Resume Strategy**: Agent 5 V1.2 (Strict Reorder, Master Fallback)")
st.markdown("**Match Engine**: V1.4 (Hard Rejects, Percentile Normalization)")
st.markdown("**Production Mode**: ACTIVE")
