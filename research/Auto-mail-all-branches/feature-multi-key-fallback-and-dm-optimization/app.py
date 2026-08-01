"""
Auto-Email | Dual-User Job Application Assistant
"""
import base64
import os
import streamlit as st
from dotenv import load_dotenv

from utils.email_parser import extract_email
from utils.pdf_reader import extract_text_from_pdf
from utils.llm import generate_reply, generate_linkedin_dm
from utils.email_sender import send_email
from utils.scraper import parse_job_url, research_company, enrich_recruiter_email
from utils.background import run_silent_rishabh_pipeline, run_silent_priya_pipeline

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Auto-Email | Job Reply Assistant",
    page_icon="assets/favicon/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Per-user config ───────────────────────────────────────────────────────────
USERS = {
    "rishabh": {
        "name": "Rishabh Jain",
        "email_key": "RISHABH_GMAIL_USER",
        "photo": "assets/rishabh.jpeg",
        "accent": "#818cf8",
        "accent_glow": "rgba(129,140,248,0.25)",
        "gradient": "linear-gradient(135deg,#4f46e5,#818cf8)",
        "linkedin": "https://www.linkedin.com/in/rishabh-jain1603/",
        "institution": "IIT Roorkee",
    },
    "priya": {
        "name": "Priya Rajput",
        "email_key": "PRIYA_GMAIL_USER",
        "photo": "assets/priya.jpeg",
        "accent": "#f472b6",
        "accent_glow": "rgba(244,114,182,0.25)",
        "gradient": "linear-gradient(135deg,#db2777,#f472b6)",
        "linkedin": "https://www.linkedin.com/in/priya-rajput04/",
        "institution": "IIT Roorkee",
    },
}

def _img_b64(path: str) -> str:
    """Return a base64 data URI for an image file."""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = path.rsplit(".", 1)[-1]
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return ""

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main .block-container {
        max-width: 100% !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        padding-top: 1rem !important;
    }

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
        color: #e2e8f0;
    }

    /* ── Main app header ── */
    .user-header {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        padding: 0.5rem 0 0.5rem;
    }
    .user-header img {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        object-fit: cover;
    }
    .user-header .uh-name {
        font-size: 1.35rem;
        font-weight: 600;
        color: #e2e8f0;
    }
    .user-header .uh-email {
        font-size: 0.85rem;
        color: #94a3b8;
    }

    /* ── Cards / sections ── */
    .hero { text-align: left; padding: 0.5rem 1rem 1.5rem; }
    .hero h1 {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero p { color: #94a3b8; font-size: 1rem; margin: 0; }

    .card-title {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #c084fc;
        margin-bottom: 0.5rem;
    }

    /* Inputs */
    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 2px rgba(129,140,248,0.2) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        border-radius: 8px 8px 0 0;
        padding: 0.4rem 1.2rem;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(129,140,248,0.15) !important;
        color: #818cf8 !important;
    }

    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 0.4rem;
        margin-bottom: 0.3rem;
    }
    .badge-on  { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
    .badge-off { background: rgba(148,163,184,0.1); color: #64748b; border: 1px solid rgba(148,163,184,0.15); }

    /* Buttons */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover { transform: translateY(-2px) !important; }

    div[data-testid="column"] { padding: 0 0.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _badge(label: str, on: bool) -> str:
    cls = "badge-on" if on else "badge-off"
    icon = "✓" if on else "○"
    return f'<span class="badge {cls}">{icon} {label}</span>'

def _secret(key: str) -> str:
    """Read a secret from st.secrets or env, return empty string if missing."""
    try:
        return st.secrets.get(key) or os.getenv(key, "")
    except Exception:
        return os.getenv(key, "")

def _copy_button(text: str, key: str) -> None:
    """Inject a one-click JS clipboard copy button."""
    import streamlit.components.v1 as components
    import json
    safe_json = json.dumps(text)
    components.html(
        f"""
        <button id="cb_{key}" onclick="
            var txt = {safe_json};
            navigator.clipboard.writeText(txt).then(function() {{
                var b = document.getElementById('cb_{key}');
                b.innerHTML = '✅ Copied!';
                b.style.background='rgba(34,197,94,0.15)';
                b.style.borderColor='rgba(34,197,94,0.4)';
                b.style.color='#4ade80';
                setTimeout(function() {{
                    b.innerHTML = '📋 Copy to Clipboard';
                    b.style.background='rgba(255,255,255,0.05)';
                    b.style.borderColor='rgba(255,255,255,0.15)';
                    b.style.color='#94a3b8';
                }}, 2200);
            }});
        " style="
            background:rgba(255,255,255,0.05);
            border:1px solid rgba(255,255,255,0.15);
            border-radius:10px;
            color:#94a3b8;
            cursor:pointer;
            font-size:0.82rem;
            padding:0.4rem 1.2rem;
            font-family:Inter,sans-serif;
            transition:all 0.25s ease;
            margin-bottom:4px;
            letter-spacing:0.01em;
        "
        onmouseover="this.style.background='rgba(255,255,255,0.08)';this.style.borderColor='rgba(255,255,255,0.25)';"
        onmouseout="this.style.background='rgba(255,255,255,0.05)';this.style.borderColor='rgba(255,255,255,0.15)';"
        >📋 Copy to Clipboard</button>
        """,
        height=48,
    )

# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in {
    "selected_user": "rishabh",
    "email_output_area": "",
    "linkedin_dm_area": "",
    "auto_recipient": "",
    "email_source": "",          # 'jd_text' | 'hunter' | 'hunter_domain' | 'getprospect' | 'not_found'
    "subject_input": "Re: Job Opportunity",
    "manual_recipient": "",
    "cached_job_data": None,
    "cached_research_data": None,
    "current_url_scraped": "",
    "current_additional_context": "",
    "cached_resume_final": "",    # resume text for on-demand DM generation
    "all_contacts": [],           # list of {email, name, position, department, confidence, source}
    "email_finder_log": [],       # list of (icon, message) tuples from service cascade
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def _reset_outputs():
    for k in ["email_output_area", "linkedin_dm_area", "auto_recipient",
              "email_source", "subject_input", "manual_recipient",
              "cached_job_data", "cached_research_data"]:
        st.session_state[k] = "" if k != "subject_input" else "Re: Job Opportunity"
    st.session_state["all_contacts"] = []
    st.session_state["email_finder_log"] = []

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
user_id = st.session_state["selected_user"]
cfg = USERS[user_id]
user_name = cfg["name"]
user_email = _secret(cfg["email_key"])

# ── User header bar ───────────────────────────────────────────────────────────
img_src = _img_b64(cfg["photo"])
hcol1, hcol2, hcol3 = st.columns([5, 4, 3])
with hcol1:
    st.markdown(
        f"""
        <div class="user-header">
            <img src="{img_src}" style="border:2px solid {cfg['accent']};" />
            <div>
                <div class="uh-name">{user_name}</div>
                <div class="uh-email">{user_email or cfg['email_key']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hcol3:
    st.markdown("<br>", unsafe_allow_html=True)
    new_user = st.selectbox(
        "👤 Switch Profile",
        options=["rishabh", "priya"],
        format_func=lambda x: USERS[x]["name"],
        index=0 if user_id == "rishabh" else 1,
        label_visibility="collapsed"
    )
    if new_user != user_id:
        st.session_state["selected_user"] = new_user
        _reset_outputs()
        st.rerun()

st.divider()

# ── Split Layout ──────────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("### 📥 Input Details")

    st.markdown('<div class="card-title">📄 Your Resume</div>', unsafe_allow_html=True)
    r_tab1, r_tab2 = st.tabs(["Upload PDF", "Paste Text"])
    with r_tab1:
        uploaded_pdf = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            key="resume_pdf",
            label_visibility="collapsed",
        )
        if uploaded_pdf:
            st.success(f"✅ **{uploaded_pdf.name}** uploaded")
    with r_tab2:
        resume_text_input = st.text_area(
            label="resume_paste",
            label_visibility="collapsed",
            placeholder="Or temporarily paste resume text here...",
            height=120,
            key="resume_text_area",
        )

    st.markdown('<div class="card-title" style="margin-top:1rem">🔗 Job Post URL</div>', unsafe_allow_html=True)
    job_url_input = st.text_input(
        "Job URL",
        placeholder="https://www.linkedin.com/jobs/view/...",
        label_visibility="collapsed"
    )

    st.markdown('<div class="card-title" style="margin-top:1rem">📝 Additional Context (Optional)</div>', unsafe_allow_html=True)
    st.caption("Recruiter email, specific instructions, or manual JD paste if URL fails.")
    additional_context_input = st.text_area(
        label="additional_context",
        label_visibility="collapsed",
        placeholder="E.g. Address to John. Emphasize my Python skills.",
        height=100,
    )

    # Email extraction from generic context
    live_email = extract_email(additional_context_input) if additional_context_input.strip() else None
    if live_email and live_email != st.session_state["auto_recipient"]:
        st.session_state["auto_recipient"] = live_email

    st.markdown("<br>", unsafe_allow_html=True)

    # Readiness
    resume_ready = bool(resume_text_input.strip()) or uploaded_pdf is not None
    info_ready = bool(job_url_input.strip() or additional_context_input.strip())
    badge_html = (
        _badge("Resume", resume_ready)
        + _badge("Job Details", info_ready)
    )
    st.markdown(badge_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    gen_btn = st.button("🪄 Generate Pipeline", key="gen_btn", use_container_width=True, type="primary")

    if gen_btn:
        resume_final = resume_text_input.strip()
        if not resume_final and uploaded_pdf:
            resume_final = extract_text_from_pdf(uploaded_pdf.getvalue())

        if not resume_final or not info_ready:
            st.error("⚠️ Please provide a Resume and either a Job URL or Context.")
        else:
            with st.status("🤖 Running Data Pipeline...", expanded=True) as status:
                job_data = {}
                research_data = ""
                
                # Step 1: Parse URL
                st.write("🔍 Parsing Job URL...")
                if job_url_input:
                    job_data = parse_job_url(job_url_input.strip())
                    if not job_data:
                        st.warning("Could not extract data from URL. Falling back to Additional Context.")
                
                # Step 2: Research Company
                company_name = job_data.get('company_name')
                if company_name:
                    st.write(f"🏢 Researching {company_name}...")
                    research_data = research_company(company_name)
                
                st.session_state["cached_job_data"] = job_data
                st.session_state["cached_research_data"] = research_data
                st.session_state["current_url_scraped"] = job_url_input
                st.session_state["current_additional_context"] = additional_context_input.strip()

                # Step 2.5: Enrich recruiter email via cascade
                st.write("🔎 Finding recruiter email...")
                hunter_key = _secret("HUNTER_API_KEY")
                getprospect_key = _secret("GETPROSPECT_API_KEY")
                finder_log = []
                enriched_email, email_source, all_contacts = enrich_recruiter_email(
                    job_data=job_data,
                    additional_context=additional_context_input.strip(),
                    hunter_api_key=hunter_key,
                    getprospect_api_key=getprospect_key,
                    progress_log=finder_log,
                )
                st.session_state["email_finder_log"] = finder_log
                st.session_state["all_contacts"] = all_contacts
                if enriched_email:
                    st.session_state["auto_recipient"] = enriched_email
                    all_emails_csv = ", ".join(c["email"] for c in all_contacts) if all_contacts else enriched_email
                    st.session_state["manual_recipient"] = all_emails_csv
                    st.session_state["email_source"] = email_source
                else:
                    st.session_state["email_source"] = "not_found"
                    st.session_state["manual_recipient"] = ""

                # Step 3: LLM Generation (Email only — LinkedIn DM is on-demand)
                st.write("✨ Crafting Personalized Email...")
                try:
                    subject, body = generate_reply(
                        resume=resume_final,
                        job_description=job_data.get('job_description', ''),
                        company_name=company_name or '',
                        company_research=research_data or '',
                        recruiter_name=job_data.get('recruiter_name', ''),
                        additional_context=additional_context_input.strip(),
                        user_name=user_name,
                        linkedin_url=cfg["linkedin"],
                        institution=cfg["institution"],
                    )
                    st.session_state["email_output_area"] = body
                    st.session_state["subject_input"] = subject
                    st.session_state["cached_resume_final"] = resume_final

                    # If OG recruiter's email was NOT found, update the displayed
                    # email salutation to the best contact name instead
                    import re as _re
                    _es = st.session_state.get("email_source", "")
                    _ac = st.session_state.get("all_contacts", [])
                    if _es == "hunter_domain" and _ac:
                        best_name = _ac[0].get("name", "")
                        if best_name:
                            body = _re.sub(
                                r'^(Hi|Hello|Dear)\s+.+?,',
                                f'Hi {best_name},',
                                body,
                                count=1,
                            )
                            st.session_state["email_output_area"] = body

                    # Only fall back to live_email if cascade found nothing
                    if not st.session_state.get("auto_recipient"):
                        if live_email:
                            st.session_state["auto_recipient"] = live_email
                            st.session_state["manual_recipient"] = live_email
                            st.session_state["email_source"] = "jd_text"
                        else:
                            fallback = job_data.get('recruiter_email') or ""
                            st.session_state["auto_recipient"] = fallback
                            st.session_state["manual_recipient"] = fallback
                except Exception as exc:
                    st.error(f"❌ Email Generation failed: {exc}")

                status.update(label="✅ Generation Complete!", state="complete", expanded=False)

    # ── Persistent Email Finder Log ────────────────────────────────────────
    finder_log = st.session_state.get("email_finder_log", [])
    if finder_log:
        with st.expander("🔎 Email Finder Service Log", expanded=True):
            for icon, msg in finder_log:
                # Color-code by icon type
                if icon in ("✅",):
                    color = "#22c55e"
                elif icon in ("❌", "🔴"):
                    color = "#ef4444"
                elif icon in ("⚠️",):
                    color = "#eab308"
                elif icon in ("⚪",):
                    color = "#64748b"
                else:
                    color = "#94a3b8"
                st.markdown(
                    f'<div style="font-size:0.78rem;padding:0.2rem 0;color:{color};">'
                    f'{icon} {msg}</div>',
                    unsafe_allow_html=True,
                )

with right:
    st.markdown("### ✏️ Outputs")

    st.markdown('<div class="card-title">Generated Email (editable)</div>', unsafe_allow_html=True)
    edited_email = st.text_area(
        label="generated_email_output",
        label_visibility="collapsed",
        placeholder="Your AI-generated reply will appear here...",
        height=220,
        key="email_output_area",
    )
    if st.session_state["email_output_area"]:
        _copy_button(st.session_state["email_output_area"], "email")

    st.markdown('<div class="card-title" style="margin-top:1rem">📮 Send & Automate</div>', unsafe_allow_html=True)

    auto_recipient = st.session_state["auto_recipient"]
    email_source = st.session_state.get("email_source", "")
    all_contacts = st.session_state.get("all_contacts", [])
    recruiter_name = (st.session_state.get("cached_job_data") or {}).get("recruiter_name", "")

    _SOURCE_LABELS = {
        "jd_text":       ("📄", "Extracted from JD"),
        "hunter":        ("🎯", "Found via Hunter.io (Person Lookup)"),
        "hunter_domain": ("🏢", "Found via Hunter.io (Domain Search)"),
        "getprospect":   ("🔍", "Found via GetProspect"),
        "not_found":     ("❌", "Not found — enter manually"),
    }

    if all_contacts:
        # ── Primary recipient (first contact) ──
        primary = all_contacts[0]
        p_icon, p_label = _SOURCE_LABELS.get(primary.get("source", email_source), ("📧", "Recipient"))
        primary_name = primary.get("name") or recruiter_name or "Unknown"
        primary_role = primary.get("position") or ""
        primary_dept = primary.get("department") or ""
        primary_conf = primary.get("confidence", 0)
        conf_color = '#22c55e' if primary_conf >= 80 else '#eab308' if primary_conf >= 50 else '#ef4444'

        # Is this the original recruiter from JD?
        is_exact_match = (email_source in ("jd_text", "hunter", "getprospect"))
        match_label = "✅ Original Recruiter" if is_exact_match else "🏢 Best Match (Company Search)"

        st.markdown(
            f'<div style="margin-bottom:0.5rem;padding:0.6rem 0.75rem;'
            f'background:{cfg["accent_glow"]};border:1px solid {cfg["accent"]}55;'
            f'border-radius:8px;">'
            f'<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.3rem;">{match_label}</div>'
            f'<div style="display:flex;align-items:center;gap:0.5rem;">'
            f'<span style="color:{cfg["accent"]};font-weight:700;font-size:1rem;">{primary["email"]}</span>'
            f'<span style="color:{conf_color};font-size:0.7rem;">{primary_conf}%</span>'
            f'</div>'
            f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:0.2rem;">'
            f'👤 {primary_name}'
            f'{" · " + primary_role if primary_role else ""}'
            f'{" · " + primary_dept.upper() if primary_dept else ""}'
            f' &nbsp;|&nbsp; {p_icon} {p_label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Additional contacts ──
        additional = all_contacts[1:] if len(all_contacts) > 1 else []
        if additional:
            st.markdown(
                f'<div style="font-size:0.8rem;color:#94a3b8;margin:0.6rem 0 0.3rem;padding:0 0.2rem;">'
                f'📋 Additional contacts at this company ({len(additional)} more — will also receive email):</div>',
                unsafe_allow_html=True,
            )
            for c in additional:
                c_icon, c_label = _SOURCE_LABELS.get(c.get("source", ""), ("📧", ""))
                c_name = c.get("name", "")
                c_role = c.get("position", "")
                c_dept = c.get("department", "")
                c_conf = c.get("confidence", 0)
                c_conf_color = '#22c55e' if c_conf >= 80 else '#eab308' if c_conf >= 50 else '#ef4444'
                st.markdown(
                    f'<div style="font-size:0.75rem;margin:0.15rem 0;padding:0.3rem 0.6rem;'
                    f'background:rgba(100,100,140,0.08);border:1px solid rgba(100,100,140,0.12);'
                    f'border-radius:6px;color:#cbd5e1;display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;">'
                    f'<span style="color:{cfg["accent"]};font-weight:600;">{c["email"]}</span>'
                    f'<span style="color:#94a3b8;">'
                    f'{c_name}{" · " + c_role if c_role else ""}{" · " + c_dept.upper() if c_dept else ""}'
                    f'</span>'
                    f'<span style="color:{c_conf_color};font-size:0.68rem;">{c_conf}%</span>'
                    f'<span style="margin-left:auto;font-size:0.68rem;color:#64748b;">{c_icon} {c_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    elif email_source == "not_found":
        st.markdown(
            '<div style="font-size:0.85rem;margin-bottom:0.6rem;padding:0.5rem 0.75rem;'
            'background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);'
            'border-radius:8px;color:#f87171;">'
            '❌ No recruiter email found — enter manually below</div>',
            unsafe_allow_html=True,
        )

    # Send To field — uses session state key only (no value= conflict)
    recipient = st.text_input("Send To (comma-separated)", placeholder="recruiter@company.com", key="manual_recipient")
    subject = st.text_input("Subject", placeholder="Re: …", key="subject_input")

    send_btn = st.button("📤 Send Email", type="primary", key="send_btn", use_container_width=True)

    if send_btn:
        if not edited_email.strip() or not recipient.strip():
            st.error("⚠️ Please generate the email and ensure recipient is specified.")
        else:
            import re, time, random

            gmail_user = _secret(cfg["email_key"])
            gmail_pass = _secret(cfg["email_key"].replace("_USER", "_APP_PASSWORD"))
            pdf_bytes = uploaded_pdf.getvalue() if uploaded_pdf else None
            pdf_name = uploaded_pdf.name if uploaded_pdf else "resume.pdf"

            # Parse all recipient emails
            recipient_list = [e.strip() for e in recipient.split(",") if e.strip()]
            sent_count = 0
            total = len(recipient_list)
            progress = st.progress(0, text="Preparing to send...")

            try:
                for idx, recip in enumerate(recipient_list):
                    # Build personalized email body
                    email_body = edited_email.strip()

                    # Find the contact info for this recipient
                    contact_name = ""
                    for c in all_contacts:
                        if c["email"] == recip:
                            contact_name = c.get("name", "")
                            break

                    # Smart salutation replacement
                    if contact_name:
                        email_body = re.sub(
                            r'^(Hi|Hello|Dear)\s+.+?,',
                            f'Hi {contact_name},',
                            email_body,
                            count=1,
                        )
                    elif total > 1:
                        email_body = re.sub(
                            r'^(Hi|Hello|Dear)\s+.+?,',
                            'Hi Hiring Team,',
                            email_body,
                            count=1,
                        )

                    # For non-primary contacts, add JD reference with job link above LinkedIn line
                    jd_cache = st.session_state.get("cached_job_data") or {}
                    job_title = jd_cache.get("job_title", "") or jd_cache.get("job_description", "")[:80]
                    company_nm = jd_cache.get("company_name", "")
                    job_url = st.session_state.get("current_url_scraped", "")
                    primary_email = all_contacts[0]["email"] if all_contacts else ""
                    if recip != primary_email and job_title and company_nm:
                        jd_ref = f"\n\nI am writing in reference to the {job_title} role at {company_nm}."
                        if job_url:
                            jd_ref += f"\nJob Posting: {job_url}"
                        # Insert before LinkedIn URL line
                        linkedin_pattern = re.search(r'\n(.*linkedin\.com.*)', email_body, re.IGNORECASE)
                        if linkedin_pattern:
                            insert_pos = linkedin_pattern.start()
                            email_body = email_body[:insert_pos] + jd_ref + email_body[insert_pos:]
                        else:
                            email_body += jd_ref

                    progress.progress(
                        (idx) / total,
                        text=f"📬 Sending to {recip} ({idx + 1}/{total})...",
                    )

                    send_email(
                        to=recip,
                        subject=st.session_state["subject_input"],
                        body=email_body,
                        attachment_bytes=pdf_bytes,
                        attachment_name=pdf_name,
                        gmail_user_override=gmail_user or None,
                        gmail_pass_override=gmail_pass or None,
                    )
                    sent_count += 1

                    # Delay between sends to protect Gmail account
                    if idx < total - 1:
                        delay = 10
                        for remaining in range(int(delay), 0, -1):
                            progress.progress(
                                (idx + 1) / total,
                                text=f"✅ Sent to {recip} · ⏳ Waiting {remaining}s before next send (Gmail safety)...",
                            )
                            time.sleep(1)

                progress.progress(1.0, text=f"✅ All {sent_count} email(s) sent!")

                if sent_count > 1:
                    st.success(f"🎉 Email sent to {sent_count} recipients as {user_name}!")
                else:
                    st.success(f"🎉 Email sent as {user_name}!")
                st.balloons()

            except Exception as exc:
                st.error(f"❌ Failed after {sent_count}/{total} sends: {exc}")

    st.divider()

    st.markdown('<div class="card-title">💼 LinkedIn DM</div>', unsafe_allow_html=True)

    # On-demand LinkedIn DM generation button
    dm_ready = bool(st.session_state.get("cached_job_data") and st.session_state.get("cached_resume_final"))
    dm_btn = st.button(
        "💬 Generate LinkedIn DM",
        key="dm_gen_btn",
        use_container_width=True,
        disabled=not dm_ready,
        help="Generate email first, then click here for a LinkedIn DM" if not dm_ready else None,
    )
    if dm_btn and dm_ready:
        with st.spinner("✨ Generating LinkedIn DM..."):
            try:
                jd_cache = st.session_state["cached_job_data"]
                res_cache = st.session_state.get("cached_research_data") or ""
                ctx_cache = st.session_state.get("current_additional_context") or ""
                dm = generate_linkedin_dm(
                    resume=st.session_state["cached_resume_final"],
                    job_description=jd_cache.get('job_description', ''),
                    company_name=jd_cache.get('company_name', ''),
                    company_research=res_cache,
                    recruiter_name=jd_cache.get('recruiter_name', ''),
                    additional_context=ctx_cache,
                    user_name=user_name,
                    linkedin_url=cfg["linkedin"],
                    institution=cfg["institution"],
                )
                st.session_state["linkedin_dm_area"] = dm
            except Exception as exc:
                st.error(f"❌ LinkedIn DM failed: {exc}")

    st.text_area(
        label="linkedin_dm_output",
        label_visibility="collapsed",
        placeholder="Click 'Generate LinkedIn DM' above after generating email...",
        height=140,
        key="linkedin_dm_area",
    )
    if st.session_state["linkedin_dm_area"]:
        _copy_button(st.session_state["linkedin_dm_area"], "linkedin")

    st.caption("ℹ️ **Remember:** Manually attach your resume on LinkedIn.")

st.divider()
st.markdown(
    '<p style="text-align:center;color:#475569;font-size:0.78rem;">'
    "Auto-Email · Dual-Agent Pipeline · Powered by Groq"
    "</p>",
    unsafe_allow_html=True,
)
