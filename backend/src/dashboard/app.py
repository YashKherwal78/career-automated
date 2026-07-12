import os
import sys

# Ensure absolute imports work when run via streamlit from root or anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st

st.set_page_config(
    page_title="CareerAutomated Control Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme is handled by .streamlit/config.toml, but we can't easily create that here. We'll rely on Streamlit's default dark mode if user's OS is dark, or we can write the config.toml later.

# Auto refresh every 30 seconds
# A simple way without st_autorefresh is to use a fragment or custom JS, but Streamlit has a built-in st.empty() or just a manual button if auto isn't strictly native. Wait, I can just use st.rerun with a time.sleep in a thread, but the safest way without plugins is a meta refresh tag.
st.markdown(
    """
    <meta http-equiv="refresh" content="30">
    <style>
        .block-container { padding-top: 1rem; }
    </style>
    """,
    unsafe_allow_html=True
)

pages = {
    "Control Center": [
        st.Page("pages/home.py", title="Home", icon="🏠"),
        st.Page("pages/jobs.py", title="Jobs", icon="💼"),
        st.Page("pages/applications.py", title="Applications", icon="📝"),
        st.Page("pages/outreach.py", title="Outreach", icon="📧"),
        st.Page("pages/queue.py", title="Queue", icon="🔄"),
        st.Page("pages/candidate.py", title="Candidate", icon="👤"),
        st.Page("pages/agents.py", title="Agents", icon="🤖"),
        st.Page("pages/analytics.py", title="Analytics", icon="📊"),
        st.Page("pages/settings.py", title="Settings", icon="⚙️")
    ]
}

pg = st.navigation(pages)
pg.run()
