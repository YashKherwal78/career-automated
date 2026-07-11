import streamlit as st
import json
import os
from src.config.config import Config

st.title("Candidate Intelligence")

profile_path = os.path.join(Config.DATA_DIR, "context", "master_candidate_profile.json")

if not os.path.exists(profile_path):
    st.warning("Master Candidate Profile not found.")
else:
    with open(profile_path, "r") as f:
        try:
            profile = json.load(f)
        except Exception as e:
            st.error(f"Failed to load profile: {e}")
            profile = {}
            
    if profile:
        st.subheader(f"{profile.get('personal_info', {}).get('name', 'Candidate Profile')}")
        st.markdown(f"**Email**: {profile.get('personal_info', {}).get('email', 'N/A')}")
        st.markdown(f"**LinkedIn**: {profile.get('personal_info', {}).get('linkedin', 'N/A')}")
        
        st.divider()
        st.subheader("Top Projects")
        for proj in profile.get('projects', []):
            with st.expander(f"{proj.get('name', 'Unnamed')}"):
                st.markdown(f"**Description**: {proj.get('description', '')}")
                st.markdown(f"**Tech Stack**: {', '.join(proj.get('technologies', []))}")
                
        st.divider()
        st.subheader("Skills")
        skills = profile.get('skills', {})
        if isinstance(skills, list):
            st.write(", ".join(skills))
        elif isinstance(skills, dict):
            for cat, s_list in skills.items():
                st.markdown(f"**{cat}**: {', '.join(s_list)}")
                
        st.divider()
        st.subheader("Experience")
        for exp in profile.get('experience', []):
            with st.expander(f"{exp.get('role', '')} @ {exp.get('company', '')}"):
                st.markdown(f"**Duration**: {exp.get('duration', '')}")
                for bullet in exp.get('bullets', []):
                    st.markdown(f"- {bullet}")
